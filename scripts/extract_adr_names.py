"""Read the Dutch proper shipping names out of ADR 2025, table A.

The app knows every UN number by its English and its German name, because the
Table A export it was built on carries those two columns. It carries no Dutch
one, and for a long time the conclusion drawn from that — written down in four
places — was that the ADR has no Dutch name. It has. The ADR is published in an
official Dutch edition, and column (2) of table A there reads BENZINE, ZOUTZUUR,
LITHIUM-ION-BATTERIJEN. Only the export did not have it.

This script reads that column. Column (2) is the one part of table A that cannot
be replaced by anything else: a threshold can be looked up somewhere else, a
name cannot.

**The book itself does not go into this repository.** What is written down is the
derived fact — the name per UN number — the same rule that
`docs/data-sources.md` states for every other regulatory source. The PDF stays
on the machine of whoever holds the licence, and is passed with ``--pdf``.

## Why two documents are read

A table read by machine does not usually fall over; it shifts a column, and then
2,000 substances quietly carry the wrong name. So the same data is read twice,
from two documents that are typeset independently of each other: table A (sorted
by UN number) and the alphabetical index (sorted by name, and thereby with
different column widths and different line breaks). Where the two agree, the
reading is right. Where they do not, it says so, and below a threshold nothing is
written down at all.

## What is hard about this table

* **The UN number and the name form one word.** "1202DIESELOLIE" — column (1)
  and column (2) run together in the text layer, so the split has to be made on
  the four digits, not on a position.
* **The table draws no column lines.** Only the numbering "(1) (2) (3a) …" above
  the header gives away where a column stands, and those positions differ per
  page: the columns are laid out anew per page. The right-hand edge of the name
  is therefore measured per page, against where the class in column (3a) begins.
* **The UN number is vertically centred in its cell.** With a name across three
  lines it stands beside the *second*, so "starts at a UN number" does not
  delimit a row. What does delimit it is the line spacing: 14.2 points within a
  name, at least 28 between two entries.
* **A name breaks after a hyphen.** "lithium-\nion-polymeer" closes up,
  "verspreidings-, uitstoot-\nof voortdrijvende lading" does not. What tells them
  apart is the word after the break.

Usage::

    python scripts/extract_adr_names.py --pdf ~/adr2025/ADR-2025-NL-Tabel-A.pdf \\
        --index ~/adr2025/ADR-2025-NL-Alfabetische-Index.pdf
    python scripts/extract_adr_names.py --pdf … --index … --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SEED = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg"

SOURCE_NAME = ("ADR 2025, Nederlandse uitgave — tabel A van hoofdstuk 3.2, "
               "kolom (2) 'Benaming en beschrijving', met de alfabetische "
               "index als tweede lezing")

#: The column numbers stand in one band above the table; a page that shows at
#: least this many of them has a readable header.
MARKERS_NEEDED = 15
MARKER = re.compile(r"^\((\d{1,2}[ab]?)\)$")

#: Everything below this y is the running foot ("ADR 2025 NL   53 / 294").
BODY_BOTTOM = 812.0

#: Where a row begins: four digits, possibly with the name stuck to them.
UN_START = re.compile(r"^\s*(\d{4})\s*")

#: What column (3a) holds: a class or a division, never a word. Used to find
#: where that column begins and thus where the name has to stop.
CLASS_VALUE = re.compile(r"^\d(\.\d)?[A-Z]?$")

#: Within a name the lines lie 14.2 points apart, between two entries at least
#: 28. Anything above this is a new entry.
ROW_GAP = 21.0

#: The parenthetical additions with which table A distinguishes several rows of
#: one UN number. They set the tank and the packing apart, not the substance:
#: the proper shipping name of UN 1993 is "BRANDBARE VLOEISTOF, N.E.G." for all
#: five rows. Kept out of the name, so that one UN number does not end up with
#: five variants of the same sentence.
ROW_QUALIFIER = re.compile(
    r"\s*\((?:dampdruk|dampspanning|met een vlampunt)\b[^()]*(?:\([^()]*\)[^()]*)*\)\s*$"
)

#: A hanging hyphen — "verspreidings-, uitstoot- of voortdrijvende lading" — is
#: always followed by one of these. A hyphen at a line break is not.
CONJUNCTION = re.compile(r"^(of|en|dan|noch)\b")


def markers(page) -> tuple[float | None, dict[str, float]]:
    """The band with the column numbers, and the centre of each of them."""
    rows: dict[float, dict[str, float]] = defaultdict(dict)
    for x0, y0, x1, _y1, word, *_ in page.get_text("words"):
        found = MARKER.match(word.strip())
        if found:
            rows[round(y0, 1)][found.group(1)] = (x0 + x1) / 2
    for y in sorted(rows):
        if len(rows[y]) >= MARKERS_NEEDED:
            return y, rows[y]
    return None, {}


def name_right(page, top: float, found: dict[str, float]) -> float | None:
    """Where the name column ends on this page.

    Not derived from the column numbers but from the class values themselves.
    The number "(3a)" stands centred above its column, and the estimate that
    follows from it — halfway to "(3b)" — is some nine points too far left;
    enough to cut off the last word of a long name. Where the class *stands* is
    exact, and the name never reaches past it.
    """
    if "3a" not in found or "3b" not in found:
        return None
    centre = found["3a"]
    lefts = [w[0] for w in page.get_text("words")
             if top <= w[1] <= BODY_BOTTOM
             and CLASS_VALUE.match(w[4])
             and abs((w[0] + w[2]) / 2 - centre) <= 15]
    if lefts:
        return min(lefts)
    # A page with too few rows to measure on falls back on the estimate; it is
    # a little tight, and the cross-check reports what that costs.
    return centre - (found["3b"] - centre) / 2


def name_lines(page, top: float, right: float) -> list[tuple[float, float, str]]:
    """The text lines of the name column, read character by character.

    Per character, because neither of the coarser units survives this table. A
    *word* runs together with what stands beside it when the gap is small
    enough, and the class in column (3a) stands right against the end of the
    name: "met inerte kop" plus class 1 came back as the single word "kop1". A
    *span* covers a whole line at once and then falls entirely outside the
    column as soon as one character does.
    """
    lines: list[tuple[float, float, str]] = []
    for block in page.get_text("rawdict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            kept = []
            for span in line["spans"]:
                for char in span["chars"]:
                    x0, y0, x1, _y1 = char["bbox"]
                    if top <= y0 <= BODY_BOTTOM and (x0 + x1) / 2 < right:
                        kept.append((x0, char["c"]))
            if kept:
                kept.sort()
                lines.append((round(line["bbox"][1], 1), line["bbox"][0],
                              "".join(c for _x, c in kept)))
    lines.sort()
    return lines


def join(previous: str, following: str) -> str:
    """Put two lines of one name together.

    A name that does not fit the column breaks after a hyphen, and that hyphen
    belongs to the word: "lithium-" and "ion-polymeer-batterijen" close up. The
    ADR also writes a shared suffix with a hanging hyphen — "verspreidings-,
    uitstoot- of voortdrijvende lading" — and there the space is part of the
    text. Two things tell them apart: a hanging hyphen is followed by a
    conjunction, and a dash used as a separator ("VRIJGESTELD COLLO -
    INSTRUMENTEN") has a space before it.
    """
    previous = previous.rstrip()
    following = following.lstrip()
    if (previous.endswith("-") and not previous.endswith(" -")
            and not CONJUNCTION.match(following)):
        return previous + following
    return f"{previous} {following}"


def read_page(page, number: int) -> tuple[list[dict[str, Any]], list[str]]:
    top_marker, found = markers(page)
    if top_marker is None:
        return [], [f"p{number}: geen kolomnummers gevonden"]
    top = top_marker + 10
    right = name_right(page, top, found)
    if right is None:
        return [], [f"p{number}: geen bruikbare kolomindeling"]

    bands: list[list[tuple[float, float, str]]] = []
    current: list[tuple[float, float, str]] = []
    previous_y: float | None = None
    for line in name_lines(page, top, right):
        if previous_y is not None and line[0] - previous_y > ROW_GAP:
            bands.append(current)
            current = []
        previous_y = line[0]
        current.append(line)
    if current:
        bands.append(current)

    rows, problems = [], []
    for band in bands:
        texts = [re.sub(r"\s+", " ", text).strip() for _y, _x, text in band]
        texts = [text for text in texts if text]
        if not texts:
            continue
        numbered = [text for text in texts if UN_START.match(text)]
        if len(numbered) > 1:
            problems.append(f"p{number}: {len(numbered)} UN-nummers in één rij")
            continue
        un = UN_START.match(numbered[0]).group(1) if numbered else None
        name = ""
        for text in texts:
            if numbered and text is numbered[0]:
                text = UN_START.sub("", text, count=1)
            if not text:
                continue
            name = join(name, text) if name else text
        rows.append({"un": un, "name_nl": name, "page": number})
    return rows, problems


def read(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Every row of a table A document, in the order it stands in."""
    import fitz

    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    with fitz.open(path) as document:
        for index in range(document.page_count):
            page_rows, page_problems = read_page(document[index], index + 1)
            problems.extend(page_problems)
            for row in page_rows:
                if row["un"] is not None:
                    rows.append(row)
                    continue
                # An entry whose name runs over the page break: the tail belongs
                # to the row that began at the foot of the previous page.
                if not rows:
                    problems.append(f"p{row['page']}: staartrij zonder voorganger")
                    continue
                rows[-1]["name_nl"] = join(rows[-1]["name_nl"], row["name_nl"])
    return rows, problems


def base_name(name: str) -> str:
    """The name without the additions that only set two table rows apart."""
    previous = None
    while previous != name:
        previous = name
        name = ROW_QUALIFIER.sub("", name).strip()
    return name


def by_un(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    """The distinct names per UN number, in the order table A gives them."""
    names: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        name = base_name(row["name_nl"])
        if name and name not in names[row["un"]]:
            names[row["un"]].append(name)
    return dict(names)


def cross_check(table: dict[str, list[str]], index: dict[str, list[str]]) -> dict[str, Any]:
    """Lay the two readings against each other.

    Only in one direction: every name table A gives has to appear in the index.
    Not the other way round, because the index lists a substance under each of
    its synonyms and therefore knows names table A does not put in column (2).
    """
    same, differs, examples = 0, 0, []
    for un, names in table.items():
        known = set(index.get(un, []))
        if set(names) <= known:
            same += 1
            continue
        differs += 1
        if len(examples) < 15:
            missing = sorted(set(names) - known)
            examples.append(f"UN {un}: tabel {missing[:1]!r} niet in index "
                            f"{sorted(known)[:1]!r}")
    total = same + differs
    return {"same": same, "differs": differs, "examples": examples,
            "agreement": round(same / total, 4) if total else None}


def against_known(table: dict[str, list[str]]) -> dict[str, Any]:
    """What the reading says about the UN numbers the app already holds.

    A number known by both is a number the reading did not invent. What differs
    is worth reporting rather than hiding: the app's table is a 2023 export, so
    the entries ADR 2025 added stand out here.
    """
    try:
        known = {str(entry.get("un")) for entry
                 in json.loads((SEED / "un_numbers.json").read_text(encoding="utf-8"))}
    except (OSError, ValueError):  # pragma: no cover - seed missing
        return {"agreement": None}
    read_uns = set(table)
    shared = read_uns & known
    return {
        "same": len(shared),
        "differs": len(known - read_uns),
        "only_in_adr_2025": sorted(read_uns - known),
        "only_in_the_app": sorted(known - read_uns),
        "agreement": round(len(shared) / len(known), 4) if known else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True,
                        help="Tabel A van de Nederlandse ADR-uitgave")
    parser.add_argument("--index", type=Path, required=True,
                        help="De alfabetische index van dezelfde uitgave")
    parser.add_argument("--out", type=Path, default=SEED / "adr_names_nl.json")
    parser.add_argument("--edition", default="ADR 2025")
    parser.add_argument("--dry-run", action="store_true",
                        help="Wel lezen en controleren, niet wegschrijven")
    parser.add_argument("--min-agreement", type=float, default=0.99,
                        help="Onder deze overeenstemming wordt niets vastgelegd")
    args = parser.parse_args(argv)

    table_rows, table_problems = read(args.pdf)
    index_rows, index_problems = read(args.index)
    table = by_un(table_rows)
    index = by_un(index_rows)

    summary = {
        "table_rows": len(table_rows), "table_un_numbers": len(table),
        "index_rows": len(index_rows), "index_un_numbers": len(index),
        "unreadable_rows": len(table_problems) + len(index_problems),
    }
    print(f"gelezen: {summary}")
    for problem in (table_problems + index_problems)[:10]:
        print("  ", problem)
    if not table:
        print("Geen namen gelezen.")
        return 1

    checks = {"index": cross_check(table, index), "un_numbers": against_known(table)}
    print("\n--- zelfcontrole ---")
    for name, result in checks.items():
        print(f"  {name}: {result.get('same')} gelijk, {result.get('differs')} anders, "
              f"overeenstemming {result.get('agreement')}")
        for example in result.get("examples", []):
            print(f"      {example}")
    if checks["un_numbers"].get("only_in_adr_2025"):
        print(f"  alleen in ADR 2025: {checks['un_numbers']['only_in_adr_2025']}")
    if checks["un_numbers"].get("only_in_the_app"):
        print(f"  alleen in de app:   {checks['un_numbers']['only_in_the_app']}")

    weakest = [result["agreement"] for result in checks.values()
               if result.get("agreement") is not None]
    if not weakest:
        print("\nNiets te vergelijken; er wordt niets vastgelegd.")
        return 1
    if min(weakest) < args.min_agreement:
        print(f"\nOvereenstemming {min(weakest)} ligt onder {args.min_agreement}: "
              "de lezing klopt niet. Er wordt niets vastgelegd.")
        return 1

    payload = {
        "_comment": ("Nederlandse benamingen uit tabel A van het ADR, machinaal "
                     "gelezen door scripts/extract_adr_names.py. Feitelijke "
                     "invulhulp; de gepubliceerde tekst van het ADR blijft "
                     "leidend."),
        "edition": args.edition,
        "source": SOURCE_NAME,
        "summary": summary,
        "cross_check": checks,
        "names": {un: names for un, names in sorted(table.items())},
    }
    document = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    print(f"\n{len(table)} UN-nummers, {len(document.encode('utf-8'))} bytes")

    if args.dry_run:
        print("Proefrun; er wordt niets vastgelegd.")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(document, encoding="utf-8")
    print(f"geschreven: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
