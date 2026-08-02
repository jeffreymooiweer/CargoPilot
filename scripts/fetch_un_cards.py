#!/usr/bin/env python3
"""Download the UN cards once and give every file the UN number as its name.

The source numbers its files sequentially (`part1`, `part2`, … `part2900`) with
no relation to the UN number on the card, so every document has to be opened and
read to find out what it is. This script does that:

1. downloads each part, politely and with retries;
2. reads the UN number from the document itself;
3. verifies it against `backend/seed/dg/un_numbers.json` — a number that is not a
   real UN entry is rejected, and the proper shipping name on the card is compared
   with the name in the database;
4. saves it as `un_1033.pdf` and records what happened in a manifest.

Anything it cannot identify with confidence is left in `_unidentified/` and listed
in the manifest, so it can be checked by hand rather than silently mislabelled —
a card filed under the wrong UN number is worse than a missing one.

Run it from GitHub Actions (`.github/workflows/fetch-un-cards.yml`); the runner has
the internet access this needs.

    python scripts/fetch_un_cards.py \
        --base-url "https://example.org/dgl/part{n}.pdf" \
        --first 1 --last 2900 --out un_cards
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - the workflow installs it
    fitz = None

REPO = Path(__file__).resolve().parents[1]
UN_DATABASE = REPO / "backend" / "seed" / "dg" / "un_numbers.json"

USER_AGENT = "CargoPilot-card-fetcher/1.0 (+https://github.com/jeffreymooiweer/CargoPilot)"

# Cantell's IMDG UN cards, 2023 edition (IMDG 41-22). One card per UN number,
# numbered sequentially in ascending UN order.
DEFAULT_BASE_URL = (
    "https://www.cantell.dk/image/catalog/Stofliste/IMDG_EN/imdg_2023_-_en_part{n}.pdf"
)

# "UN 1033", "UN1033", "UN-1033". The prefix is what makes a four-digit number a
# UN number rather than a page number, a year or a phone extension.
UN_PREFIXED = re.compile(r"\bUN[\s \-./]{0,3}(\d{4})\b", re.IGNORECASE)
BARE_FOUR_DIGITS = re.compile(r"\b(\d{4})\b")

# Confidence levels recorded in the manifest.
CONFIRMED = "confirmed"    # UN number found and the shipping name matches
PROBABLE = "probable"      # UN number found and valid, name could not be compared
UNCERTAIN = "uncertain"    # something was found but it does not hold up
MISSING = "missing"        # nothing usable in the document


def log(message: str) -> None:
    print(message, flush=True)


def normalise(text: str) -> str:
    """Lower-case, strip accents and punctuation — for comparing shipping names."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower())


def name_tokens(name: str) -> set[str]:
    """Meaningful words of a proper shipping name."""
    stop = {
        "or", "and", "with", "the", "of", "in", "a", "an", "not", "otherwise",
        "specified", "nos", "n", "o", "s", "by", "mass", "than", "less", "more",
        "solution", "mixture", "contained", "containing", "type", "class",
    }
    return {w for w in normalise(name).split() if len(w) > 2 and w not in stop}


@dataclass
class UnEntry:
    un: str
    names: list[str] = field(default_factory=list)

    def best_name_overlap(self, haystack: set[str]) -> float:
        """How well the best of our names for this UN matches the card's text.

        Scored per name, not over all names pooled together: a card printed in
        English should not be marked down because we also hold a German name
        whose words are nowhere on the page.
        """
        best = 0.0
        for name in self.names:
            tokens = name_tokens(name)
            if tokens:
                best = max(best, len(tokens & haystack) / len(tokens))
        return best


def load_un_database() -> dict[str, UnEntry]:
    """UN number → the names we know for it, from the bundled ADR table."""
    raw = json.loads(UN_DATABASE.read_text(encoding="utf-8"))
    entries: dict[str, UnEntry] = {}
    for row in raw:
        un = str(row.get("un") or "").strip().zfill(4)
        if not un.isdigit():
            continue
        entry = entries.setdefault(un, UnEntry(un=un))
        for key in ("name_en", "name_nl", "name_de"):
            value = str(row.get(key) or "").strip()
            if value and value not in entry.names:
                entry.names.append(value)
    return entries


def download(url: str, attempts: int = 4, timeout: int = 60) -> bytes | None:
    """Fetch one file, backing off on failure. Returns None on a hard 404."""
    delay = 2.0
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            log(f"    HTTP {exc.code} on attempt {attempt}")
        except Exception as exc:  # noqa: BLE001 - network is allowed to be flaky
            log(f"    {type(exc).__name__} on attempt {attempt}: {exc}")
        if attempt < attempts:
            time.sleep(delay)
            delay *= 2
    return None


def extract_spans(data: bytes) -> tuple[list[tuple[str, float, float]], str]:
    """Text spans as (text, font size, y position) plus the full text of page 1.

    Font size and position are what separate the UN number in the card's heading
    from one mentioned in a paragraph of body text.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF is required; pip install pymupdf")
    spans: list[tuple[str, float, float]] = []
    full_text = ""
    with fitz.open(stream=data, filetype="pdf") as pdf:
        if pdf.page_count == 0:
            return spans, ""
        page = pdf[0]
        full_text = page.get_text()
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        spans.append((text, float(span["size"]), float(span["bbox"][1])))
    return spans, full_text


# The cards are laid out as label/value pairs: a line reading "UN number"
# followed by the number itself, and a footer repeating "UN 0004". Reading those
# beats guessing from font size, so it is tried first.
UN_LABEL = "un number"
CARD_FOOTER = re.compile(r"\bUN\s?(\d{3,4})\b")


def identify_from_labels(full_text: str) -> tuple[str | None, str | None, list[str]]:
    """Read the UN number from the card's own "UN number" field.

    Returns (value under the label, value in the footer, all footer values).
    The two are cross-checked by the caller: a card whose heading and footer
    disagree is not something to file on a coin flip.
    """
    lines = [line.strip() for line in full_text.split("\n")]
    lines = [line for line in lines if line]

    labelled: str | None = None
    for index, line in enumerate(lines):
        if line.lower() == UN_LABEL:
            for following in lines[index + 1: index + 4]:
                if re.fullmatch(r"\d{3,4}", following):
                    labelled = following.zfill(4)
                    break
            break

    footers = [m.group(1).zfill(4) for m in CARD_FOOTER.finditer(full_text)]
    footer = footers[-1] if footers else None
    return labelled, footer, footers


def candidate_un_numbers(
    spans: list[tuple[str, float, float]],
    full_text: str,
) -> list[tuple[str, float]]:
    """UN numbers found in the document, best first, with a score each."""
    scores: dict[str, float] = {}

    def add(un: str, score: float) -> None:
        scores[un] = max(scores.get(un, 0.0), score)

    biggest = max((size for _text, size, _y in spans), default=0.0)
    for text, size, y in spans:
        for match in UN_PREFIXED.finditer(text):
            # Prefixed with "UN", so almost certainly a UN number. Weight it by
            # how prominent it is: big type near the top is the card's subject.
            score = 100.0
            if biggest and size >= biggest * 0.8:
                score += 40.0
            elif biggest and size >= biggest * 0.6:
                score += 20.0
            if y < 200:
                score += 20.0
            add(match.group(1), score)

    # Some cards print the number without the "UN" prefix in the heading.
    for text, size, y in spans:
        if biggest and size >= biggest * 0.8 and y < 250:
            for match in BARE_FOUR_DIGITS.finditer(text):
                add(match.group(1), 60.0)

    # Last resort: anywhere in the running text.
    for match in UN_PREFIXED.finditer(full_text):
        add(match.group(1), 40.0)

    return sorted(scores.items(), key=lambda item: -item[1])


def identify(
    data: bytes,
    database: dict[str, UnEntry],
) -> tuple[str | None, str, dict[str, object]]:
    """Work out which UN number a card is about.

    Returns (un number or None, confidence, details for the manifest).
    """
    spans, full_text = extract_spans(data)
    details: dict[str, object] = {
        "has_text_layer": bool(full_text.strip()),
        "heading": " ".join(t for t, _s, _y in spans[:3])[:120],
    }

    if not full_text.strip():
        details["note"] = "no text layer — the document is probably a scan (needs OCR)"
        return None, MISSING, details

    haystack_early = name_tokens(full_text)

    # Preferred route: the card states its own UN number under a label, and
    # repeats it in the footer. Both agreeing, on a number that exists in the
    # ADR table, is as certain as this gets.
    labelled, footer, _footers = identify_from_labels(full_text)
    if labelled:
        details["labelled_un"] = labelled
        details["footer_un"] = footer
        entry = database.get(labelled)
        if entry is None:
            details["note"] = f"the card names UN {labelled}, which is not in the ADR table"
        elif footer and footer != labelled:
            # The card contradicts itself. Which half is wrong is anyone's guess,
            # and guessing is exactly what must not happen here — park it.
            details["note"] = (
                f"the card's heading says UN {labelled} but its footer says UN {footer}"
            )
            return None, UNCERTAIN, details
        else:
            overlap = entry.best_name_overlap(haystack_early)
            details["name_match"] = round(overlap, 2)
            details["name_in_database"] = entry.names[0] if entry.names else ""
            details["source"] = "label"
            return labelled, CONFIRMED if overlap >= 0.4 else PROBABLE, details

    candidates = candidate_un_numbers(spans, full_text)
    details["candidates"] = [un for un, _score in candidates[:5]]
    if not candidates:
        details["note"] = "no UN number found in the document"
        return None, MISSING, details

    details["source"] = "heuristic"
    haystack = haystack_early
    for un, score in candidates:
        entry = database.get(un)
        if entry is None:
            continue  # A four-digit number that is not a real UN entry.
        overlap = entry.best_name_overlap(haystack)
        if overlap >= 0.4:
            details["name_match"] = round(overlap, 2)
            details["name_in_database"] = entry.names[0]
            return un, CONFIRMED, details
        if score >= 100:
            details["name_in_database"] = entry.names[0] if entry.names else ""
            details["note"] = "UN number is valid but the shipping name could not be matched"
            return un, PROBABLE, details

    details["note"] = "no candidate matched a known UN number"
    return None, UNCERTAIN, details


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help="URL with {n} where the part number goes")
    parser.add_argument("--first", type=int, default=1)
    parser.add_argument("--last", type=int, default=2900)
    parser.add_argument("--out", default="un_cards", help="output directory")
    parser.add_argument("--delay", type=float, default=0.4,
                        help="seconds between requests — be a good guest")
    parser.add_argument("--limit", type=int, default=0,
                        help="stop after N parts (for a trial run)")
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and identify, but write nothing")
    args = parser.parse_args()

    if "{n}" not in args.base_url:
        parser.error("--base-url must contain {n}")

    out_dir = Path(args.out)
    unidentified_dir = out_dir / "_unidentified"
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        unidentified_dir.mkdir(parents=True, exist_ok=True)

    database = load_un_database()
    log(f"UN database: {len(database)} numbers")

    manifest: dict[str, dict[str, object]] = {}
    used: dict[str, int] = {}
    previous_un: str | None = None
    counts = {CONFIRMED: 0, PROBABLE: 0, UNCERTAIN: 0, MISSING: 0, "absent": 0,
              "out_of_sequence": 0}

    numbers = range(args.first, args.last + 1)
    if args.limit:
        numbers = range(args.first, min(args.last, args.first + args.limit - 1) + 1)

    for n in numbers:
        part = f"part{n}"
        url = args.base_url.replace("{n}", str(n))
        data = download(url)
        if data is None:
            counts["absent"] += 1
            manifest[part] = {"status": "absent", "url": url}
            log(f"{part}: not available")
            time.sleep(args.delay)
            continue

        try:
            un, confidence, details = identify(data, database)
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop 2900
            un, confidence, details = None, UNCERTAIN, {"note": f"{type(exc).__name__}: {exc}"}

        counts[confidence] = counts.get(confidence, 0) + 1
        record: dict[str, object] = {"status": confidence, "url": url, **details}

        if un and previous_un and un < previous_un:
            # The parts ascend by UN number. A step backwards means either a gap
            # in the source or a misread card; either way, look at it by hand.
            record_note = f"out of sequence: follows UN {previous_un}"
            details["note"] = f"{details.get('note', '')} {record_note}".strip()
            counts["out_of_sequence"] = counts.get("out_of_sequence", 0) + 1

        if un:
            previous_un = un
            seen = used.get(un, 0) + 1
            used[un] = seen
            filename = f"un_{un}.pdf" if seen == 1 else f"un_{un}-{seen}.pdf"
            record["un"] = un
            record["file"] = filename
            if seen > 1:
                record["note"] = f"another card already claimed UN {un}"
            target = out_dir / filename
            log(f"{part}: UN {un} ({confidence}) -> {filename}")
        else:
            filename = f"{part}.pdf"
            record["file"] = f"_unidentified/{filename}"
            target = unidentified_dir / filename
            log(f"{part}: not identified ({confidence}) — {details.get('note', '')}")

        if not args.dry_run:
            target.write_bytes(data)

        manifest[part] = record
        time.sleep(args.delay)

    identified = counts[CONFIRMED] + counts[PROBABLE]
    summary = {
        "source": args.base_url,
        "range": [args.first, args.last],
        "parts_seen": len(manifest),
        "identified": identified,
        "unique_un_numbers": len(used),
        "counts": counts,
    }
    log("")
    log(json.dumps(summary, indent=2))

    if not args.dry_run:
        (out_dir / "manifest.json").write_text(
            json.dumps({"summary": summary, "parts": manifest}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        log(f"\nWrote {out_dir / 'manifest.json'}")

    # Nothing identified at all means the URL pattern is wrong, or the documents
    # are scans. Fail loudly rather than committing an empty folder.
    if identified == 0:
        log("\nERROR: not a single card could be identified.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
