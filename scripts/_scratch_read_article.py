#!/usr/bin/env python3
"""Temporary: read an article and its figures on a runner and print them.

The development container's egress policy blocks medium.com, so an article the
user wants analysed cannot be opened here. A runner can reach it. This prints
the prose to the log and each figure as base64 JPEG, small enough to travel in a
log line, so the images can be reconstructed and actually looked at rather than
guessed at from their captions.

Scratch file. Delete once the article has been read — it is not part of
CargoPilot and must not survive into a release.
"""
from __future__ import annotations

import base64
import io
import re
import subprocess
import sys
from html import unescape

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")
MAX_WIDTH = 1000
CHUNK = 3000


def get(url: str) -> bytes:
    result = subprocess.run(
        ["curl", "-sSL", "--compressed", "--max-time", "90", "-A", UA, url],
        capture_output=True,
    )
    return result.stdout


def text_of(html: str) -> str:
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    # Keep figure captions and headings distinguishable in the flattened text.
    body = re.sub(r"(?i)<h([1-6])[^>]*>", r"\n\n### ", body)
    body = re.sub(r"(?i)<figcaption[^>]*>", "\n[CAPTION] ", body)
    body = re.sub(r"(?i)</(p|li|div|figure|figcaption|h[1-6])>", "\n", body)
    body = re.sub(r"(?i)<li[^>]*>", "\n  - ", body)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    body = unescape(body)
    body = re.sub(r"[ \t\xa0]+", " ", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def figures(html: str) -> list[str]:
    """Every distinct Medium-hosted image, largest variant, in document order."""
    urls: list[str] = []
    for match in re.finditer(r'https://miro\.medium\.com/[^\s"\'<>\\)]+', html):
        url = match.group(0).replace("&amp;", "&")
        # Medium serves many sizes; ask for a big one and drop the duplicates.
        key = re.sub(r"/(resize:|max/|fit/)[^/]*/", "/", url)
        key = re.sub(r"\?.*$", "", key)
        identifier = key.rsplit("/", 1)[-1]
        if len(identifier) < 20 or any(identifier in seen for seen in urls):
            continue
        urls.append(f"https://miro.medium.com/v2/resize:fit:{MAX_WIDTH}/{identifier}")
    return urls


def emit(index: int, url: str) -> None:
    raw = get(url)
    if len(raw) < 2000:
        print(f"[FIGURE {index}] {url} — {len(raw)} bytes, skipped")
        return
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(raw)).convert("RGB")
        if image.width > MAX_WIDTH:
            image = image.resize(
                (MAX_WIDTH, round(image.height * MAX_WIDTH / image.width)),
                Image.LANCZOS,
            )
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=72, optimize=True)
        payload = buffer.getvalue()
    except Exception as error:  # noqa: BLE001
        print(f"[FIGURE {index}] {url} — could not re-encode: {error}")
        payload = raw

    encoded = base64.b64encode(payload).decode()
    print(f"[FIGURE {index}] {url} — {len(payload)} bytes, {len(encoded)} b64")
    for start in range(0, len(encoded), CHUNK):
        print(f"[F{index}#{start // CHUNK:03d}] {encoded[start:start + CHUNK]}")
    print(f"[FIGURE {index} END]")


def main() -> None:
    url = sys.argv[1]
    # Medium's bot protection refuses datacentre addresses outright, which is
    # every runner. The Archive holds the page and does not.
    candidates = [
        f"https://web.archive.org/web/2025id_/{url}",
        f"https://web.archive.org/web/2024id_/{url}",
        f"https://web.archive.org/web/2id_/{url}",
        url,
    ]
    html = ""
    for candidate in candidates:
        body = get(candidate).decode("utf-8", "replace")
        blocked = "you have been blocked" in body.lower() or len(body) < 20000
        print(f"  {candidate[:70]} -> {len(body)} bytes"
              f"{' (blocked/short)' if blocked else ''}", file=sys.stderr)
        if not blocked:
            html = body
            break
    if not html:
        raise SystemExit("every route returned a block page or nothing usable")

    print("=" * 78)
    print("ARTICLE TEXT")
    print("=" * 78)
    print(text_of(html)[:24000])

    found = figures(html)
    print()
    print("=" * 78)
    print(f"FIGURES ({len(found)})")
    print("=" * 78)
    for index, figure in enumerate(found[:14]):
        emit(index, figure)


if __name__ == "__main__":
    main()
