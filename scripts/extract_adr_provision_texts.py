"""Extract the V, CV and S provision texts of ADR 7.2.4, 7.5.11 and 8.5.

The UN cards print these provisions the way the classic datasheets do: as the
text of the provision, not as a bare code with an article reference. That
text must come from the official edition, verbatim — a language model
summarising the law is exactly what this pipeline exists to avoid. So this
script reads the code/text tables of the official PDF geometrically: each
code (V1…V15, CV1…CV37, S1…S24) anchors a row band in the left column, and
everything printed beside and below it, until the next code, is that
provision's text.

Meant for the UNECE English edition, Volume II (the development container
cannot reach unece.org, so a GitHub runner downloads it and runs this):

    python scripts/extract_adr_provision_texts.py --pdf adr2.pdf \
        --out backend/seed/dg/adr_provision_texts.json

The output carries per-code text plus diagnostics (pages used, text lengths)
so a layout change in a future edition fails loudly and inspectably.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz

FAMILIES = {
    "V": {"pattern": r"V(\d{1,2}):?", "expected": 15, "section": "7.2.4"},
    "CV": {"pattern": r"CV(\d{1,2}):?", "expected": 38, "section": "7.5.11"},
    "S": {"pattern": r"S(\d{1,2}):?", "expected": 24, "section": "8.5"},
}

#: Lines that are page furniture, not provision text.
_NOISE = re.compile(
    r"^(-?\s*\d+\s*-?|ADR \d{4}.*|Copyright.*United Nations.*|\d+ / \d+)$")


def _anchors(page: fitz.Page, pattern: str) -> list[tuple[int, float, float]]:
    """(code number, y, x) for section-defining code tokens in the left column."""
    out = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        match = re.fullmatch(pattern, word)
        if match and x0 < page.rect.width * 0.28:
            out.append((int(match.group(1)), y0, x0))
    out.sort(key=lambda a: a[1])
    return out


def _section_pages(doc: fitz.Document, family: str) -> list[int]:
    """The contiguous run of pages that holds the family's own table.

    Citations elsewhere mention single codes; the section itself is the run
    of pages that together cover the most *distinct* codes, extended across
    anchor-less gap pages (a long provision can run over a page without a
    new code starting on it).
    """
    spec = FAMILIES[family]
    pages_with = []
    for number in range(doc.page_count):
        found = {a[0] for a in _anchors(doc[number], spec["pattern"])}
        if found:
            pages_with.append((number, found))

    runs: list[list[tuple[int, set]]] = []
    for number, found in pages_with:
        if runs and number - runs[-1][-1][0] <= 8:
            runs[-1].append((number, found))
        else:
            runs.append([(number, found)])
    if not runs:
        return []
    best = max(runs, key=lambda run: len(set().union(*(f for _, f in run))))
    return list(range(best[0][0], best[-1][0] + 1))


def _band_text(page: fitz.Page, y0: float, y1: float, x_min: float) -> list[str]:
    words = [w for w in page.get_text("words")
             if y0 - 2 <= w[1] < y1 - 2 and w[0] >= x_min]
    words.sort(key=lambda w: (round(w[1] / 4), w[0]))
    lines: list[str] = []
    current_y = None
    for x0, wy0, x1, wy1, word, *_ in words:
        if current_y is None or wy0 - current_y > 3:
            lines.append(word)
        else:
            lines[-1] += f" {word}"
        current_y = wy0
    return [line for line in lines if not _NOISE.fullmatch(line.strip())]


def extract_family(doc: fitz.Document, family: str) -> tuple[dict[str, str], dict]:
    spec = FAMILIES[family]
    pages = _section_pages(doc, family)
    texts: dict[int, list[str]] = {}
    last_code: int | None = None
    for number in pages:
        page = doc[number]
        anchors = _anchors(page, spec["pattern"])
        # Text above the first anchor continues the previous code.
        if anchors and last_code is not None and anchors[0][1] > 60:
            texts[last_code] += _band_text(page, 0, anchors[0][1], 0)
        if not anchors and last_code is not None:
            texts[last_code] += _band_text(page, 0, page.rect.height, 0)
            continue
        for i, (code, y, x) in enumerate(anchors):
            y_end = anchors[i + 1][1] if i + 1 < len(anchors) else page.rect.height
            texts.setdefault(code, [])
            texts[code] += _band_text(page, y, y_end, x + 4)
            last_code = code

    cleaned = {f"{family}{code}": "\n".join(lines).strip()
               for code, lines in sorted(texts.items())}
    diagnostics = {
        "pages": [p + 1 for p in pages],
        "codes_found": len(cleaned),
        "codes_expected": spec["expected"],
        "empty": [key for key, value in cleaned.items() if not value],
        "lengths": {key: len(value) for key, value in cleaned.items()},
    }
    return cleaned, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--families", default="V,CV,S")
    parser.add_argument("--source", default="",
                        help="provenance line recorded in the output")
    parser.add_argument("--lenient", action="store_true",
                        help="report shortfalls without failing the run")
    args = parser.parse_args()

    doc = fitz.open(str(args.pdf))
    result: dict = {
        "_comment": (
            "Provision texts of ADR 7.2.4 (V), 7.5.11 (CV) and 8.5 (S), read "
            "verbatim by machine with scripts/extract_adr_provision_texts.py "
            "for the UN cards. A compilation offered as an aid; the published "
            "text of the ADR remains authoritative."),
        "source": args.source,
        "sections": {},
        "diagnostics": {},
    }
    ok = True
    for family in [f.strip().upper() for f in args.families.split(",") if f.strip()]:
        texts, diagnostics = extract_family(doc, family)
        result["sections"][family] = texts
        result["diagnostics"][family] = diagnostics
        if diagnostics["codes_found"] < diagnostics["codes_expected"] or diagnostics["empty"]:
            ok = False
            print(f"{family}: found {diagnostics['codes_found']} of "
                  f"{diagnostics['codes_expected']}, empty: {diagnostics['empty']}",
                  file=sys.stderr)

    payload = json.dumps(result, indent=1, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if (ok or args.lenient) else 1


if __name__ == "__main__":
    raise SystemExit(main())
