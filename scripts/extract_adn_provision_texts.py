"""Extract the coded additional requirements of ADN 7.1.6, verbatim.

Table A of the ADN assigns per substance the codes of 7.1.6: ventilation
(VE01…), measures before loading (LO01…), handling and stowage (HA01…),
and measures during carriage (CO…, ST…, RA…, IN…). The UN cards print
those provisions the way the classic datasheets do — as the text of the
requirement, not as a bare code with an article reference — and that text
must come from the official edition, verbatim. Same method as
``extract_adr_provision_texts.py``: each code anchors a row band in the
left column of the section's own table, and everything printed beside and
below it, until the next code, is that requirement's text.

There is no hand-kept "expected count" here: the extraction is validated
against the codes ADN table A actually assigns
(``backend/seed/dg/adn_table_a.json``) — every code a substance carries
must come out with a text, or the run fails by name.

Meant for the UNECE English ADN 2025 (the development container cannot
reach unece.org, so a GitHub runner downloads it and runs this):

    python scripts/extract_adn_provision_texts.py --pdf adn.pdf \
        --out backend/seed/dg/adn_provision_texts.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
TABLE_A = ROOT / "backend" / "seed" / "dg" / "adn_table_a.json"

#: The code families of ADN 7.1.6, each with the two-digit shape the table
#: prints. The section that defines them is named for the card's fallback
#: reference and the provenance line.
FAMILIES = {
    "VE": {"pattern": r"VE(\d{2}):?", "section": "7.1.6.12"},
    "LO": {"pattern": r"LO(\d{2}):?", "section": "7.1.6.13"},
    "HA": {"pattern": r"HA(\d{2}):?", "section": "7.1.6.14"},
    "CO": {"pattern": r"CO(\d{2}):?", "section": "7.1.6.14"},
    "ST": {"pattern": r"ST(\d{2}):?", "section": "7.1.6.14"},
    "RA": {"pattern": r"RA(\d{2}):?", "section": "7.1.6.14"},
    "IN": {"pattern": r"IN(\d{2}):?", "section": "7.1.6.16"},
}

_NOISE = re.compile(
    r"^(-?\s*\d+\s*-?|ADN \d{4}.*|Copyright.*United Nations.*|\d+ / \d+)$")


def _anchors(page: fitz.Page, pattern: str) -> list[tuple[int, float, float]]:
    """(code number, y, x) for code tokens that start a row in the left column."""
    out = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        match = re.fullmatch(pattern, word)
        if match and x0 < page.rect.width * 0.28:
            out.append((int(match.group(1)), y0, x0))
    out.sort(key=lambda a: a[1])
    return out


def _section_pages(doc: fitz.Document, family: str) -> list[int]:
    """The contiguous run of pages holding the family's own table — the run
    covering the most distinct codes; citations elsewhere mention one or two."""
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

    cleaned = {f"{family}{code:02d}": "\n".join(lines).strip()
               for code, lines in sorted(texts.items())}
    diagnostics = {
        "pages": [p + 1 for p in pages],
        "codes_found": len(cleaned),
        "empty": [key for key, value in cleaned.items() if not value],
        "lengths": {key: len(value) for key, value in cleaned.items()},
    }
    return cleaned, diagnostics


def codes_assigned_by_table_a() -> set[str]:
    """Every 7.1.6 code some substance actually carries, normalised.

    The table prints footnote asterisks ("VE03*") and the reading kept one
    case quirk ("Ha01"); the code identity is the letters and digits.
    """
    table = json.loads(TABLE_A.read_text(encoding="utf-8"))
    used: set[str] = set()
    for entry in table["entries"]:
        for field in ("ventilation", "loading_measures"):
            for token in re.split(r"[,;\s]+", str(entry.get(field) or "")):
                token = token.strip().rstrip("*").upper()
                if re.fullmatch(r"(VE|LO|HA|CO|ST|RA|IN)\d{2}", token):
                    used.add(token)
    return used


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--source", default="",
                        help="provenance line recorded in the output")
    parser.add_argument("--lenient", action="store_true",
                        help="report shortfalls without failing the run")
    args = parser.parse_args()

    doc = fitz.open(str(args.pdf))
    result: dict = {
        "_comment": (
            "Additional requirements of ADN 7.1.6 (VE, LO, HA, CO, ST, RA, "
            "IN), read verbatim by machine with "
            "scripts/extract_adn_provision_texts.py for the UN cards. A "
            "compilation offered as an aid; the published text of the ADN "
            "remains authoritative."),
        "source": args.source,
        "sections": {},
        "diagnostics": {},
    }
    extracted: set[str] = set()
    for family in FAMILIES:
        texts, diagnostics = extract_family(doc, family)
        result["sections"][family] = texts
        result["diagnostics"][family] = diagnostics
        extracted |= {code for code, text in texts.items() if text}

    used = codes_assigned_by_table_a()
    missing = sorted(used - extracted)
    result["diagnostics"]["assigned_by_table_a"] = len(used)
    result["diagnostics"]["assigned_but_missing"] = missing
    if missing:
        print(f"table A assigns codes with no extracted text: {missing}",
              file=sys.stderr)

    payload = json.dumps(result, indent=1, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if (not missing or args.lenient) else 1


if __name__ == "__main__":
    raise SystemExit(main())
