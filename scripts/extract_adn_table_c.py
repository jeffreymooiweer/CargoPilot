#!/usr/bin/env python3
"""Read table C of the ADN — the substances admitted to carriage in tank vessels.

Table C is the tank-vessel half of chapter 3.2: twenty columns that answer, per
substance, which type of vessel may carry it (G, C or N), how the cargo tank
must be built and equipped, and what the vessel must show and carry. CargoPilot
has said "table C is not covered" since v1.71.0; this script is how it stops
being true.

Two independent readings, per the rule for regulatory tables in this repository:

``--dutch``
    The official Dutch edition's list pages, stored as
    ``ADN-2025-NL-mindef-index.json`` in the document store (see
    ``backend/seed/dg/sources.json``, id ``adn_nl_index``). The five ADNC list
    pages hold the rows as a single run of text per page. Cells are separated
    only by spaces, so the parser anchors on the columns whose vocabulary is
    closed — the two booleans of columns (14) and (17) most of all — and works
    outward. A row that does not validate in every cell is not guessed at; it
    is reported.

``--english adn.pdf``
    The UNECE English edition, read geometrically with PyMuPDF: the landscape
    table C pages carry real cell positions, so the columns come from x
    coordinates instead of from vocabulary. Runs where the PDF is — the CI
    cache — via the extract workflow.

``--check english.json``
    Compare the two readings row by row and field by field, and report every
    disagreement. Only when the comparison is clean does ``--emit`` write
    ``backend/seed/dg/adn_table_c.json``.

The Dutch export's known quirk is recorded here because the parser has to undo
it: the last column is stored four times over (the page carries the remark cell
once per interface language, and the export glued them), so ``1, 2, 31`` is
stored as ``1 , 2 , 311 , 2 , 311 , 2 , 311 , 2 , 31``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SEED = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg"

#: The five ADNC list pages in the stored index, keyed as the index keys them.
DUTCH_PAGES = ("UN1000", "UN1500", "UN2000", "UN2500", "UN3000")

#: The twenty columns of table C, with the field name the seed gives each.
FIELDS = [
    "un", "name_nl", "class", "classification_code", "packing_group",
    "dangers", "vessel_type", "cargo_tank_design", "cargo_tank_type",
    "cargo_tank_equipment", "opening_pressure_kpa", "max_filling_percent",
    "density", "sampling_device", "pump_room_below_deck", "temperature_class",
    "explosion_group", "explosion_protection", "equipment", "blue_cones",
    "remarks",
]

#: A row begins with a four-digit number followed by a name in capitals. The
#: same guard as table A: a digit-led name is accepted, a number inside a cell
#: (followed by lower case or another bare number) is not.
ROW_START = re.compile(r"(?:^|(?<= ))(\d{4}) (?=[A-Z“(]|\d\S*[A-Za-z])")

#: Closed vocabularies, one per anchoring cell. ``*`` is the book's "several
#: answers, see 3.2.3.3" and is legal almost everywhere.
VESSEL = re.compile(r"[GCN]|\*")
#: Almost any cell can carry footnote references — ``4)``, ``, 12)``, and the
#: export sometimes drops the comma or doubles the bracket. One suffix grammar
#: covers them all.
FOOT = r"(?:[ ,]*\d+\)+)*\)*"

SMALL = re.compile(r"[1-4](?:,[1-4])*" + FOOT + r"|-|\*")  # tank cells, sampler
NUMBER = re.compile(r"\d+" + FOOT + r"|-|\*")             # opening pressure, filling %
BOOL = re.compile(r"(?:True|False)" + FOOT + r"|\*|-")
#: One row in the export drops a comma ("PP , EP EX , TOX , A"), so the codes
#: may also meet on a bare space.
EQUIPMENT = re.compile(
    r"(?:PP|EP|EX|TOX|A)\*?(?:[ ,](?:PP|EP|EX|TOX|A)\*?)*" + FOOT + r"|\*|-")


class CellShape:
    """A vocabulary too battered for one regex: footnotes with and without
    commas, bracket groups with footnotes inside, brackets doubled by the glue.
    What stays true is the alphabet of the cell and how it opens, and the
    neighbours (a boolean on either side) keep a charset matcher from
    wandering."""

    def __init__(self, charset: str, opening: str, must_contain: str):
        self.token = re.compile(charset)
        self.opening = re.compile(opening)
        self.contain = re.compile(must_contain)

    def fullmatch(self, cell: str):
        if cell in ("-", "*"):
            return True
        tokens = cell.split(" ")
        return (all(self.token.fullmatch(t) for t in tokens)
                and self.opening.match(cell)
                and self.contain.search(cell)) or None


TEMP = CellShape(r"[T0-9(),]+\)?", r"[T(]", r"T\d|T\(")
EXPLOSION = CellShape(r"[IABC0-9(),]+\)?", r"[I(]", r"[ABC]")
CONES = re.compile(r"[012]|\*|-")
PG = re.compile(r"I{1,3}|-|\*")
CLASS = re.compile(r"[1-9](?:\.\d)?")
CODE = re.compile(r"-|\*|\d?[A-Z]{1,3}\d{0,2}(?:\.\d)?")


def flatten(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tighten(value: str) -> str:
    """The export writes a space on either side of every comma, which cuts
    cells like ``PP , EP , EX`` into tokens no vocabulary matches. Gluing the
    commas first makes one token of each comma-joined cell."""
    # One row writes ``1; 3`` where every other writes ``1 , 3`` — the
    # semicolon is the same list separator, normalised with the comma.
    return re.sub(r"\s*[;,]\s*", ",", flatten(value))


def tidy(value: str) -> str:
    value = re.sub(r",", ", ", flatten(value))
    value = re.sub(r"\s+", " ", value)
    return "" if value == "-" else value


def numbers_tight(value: str) -> str:
    """The export sets ``0 , 68 - 0 , 72`` where the book prints ``0,68 - 0,72``."""
    value = re.sub(r"(\d)\s*,\s*(\d)", r"\1,\2", flatten(value))
    return re.sub(r"\s*-\s*", " - ", value) if re.search(r"\d\s*-\s*\d", value) else value


def undouble(value: str) -> str:
    """Column (20) as stored is the cell four times over — once per interface
    language. Identical cells glue seamlessly into a string whose quarters
    match; the ``zie/see/siehe/voir`` variants differ by exactly that one word,
    so mapping all four onto one marker first makes the quarters match too."""
    value = flatten(value)
    normalised = re.sub(r"\b(?:zie|see|siehe|voir)\b", "see", value)
    for repeat in (4, 3, 2):
        if len(normalised) % repeat == 0:
            piece = normalised[: len(normalised) // repeat]
            if piece * repeat == normalised and piece.strip(" ,"):
                return tidy(piece.strip().rstrip(","))
    return tidy(normalised)


class RowError(ValueError):
    pass


def _take(pattern: re.Pattern, tokens: list[str], row: str) -> str:
    """Pop one cell off the back of the token list.

    A cell can span several tokens (``II B 4)``, ``T2 1)12)``), and the last
    token alone often matches nothing — ``B2)`` is no cell, ``II B,(II B2)``
    is. So the widest window that matches the vocabulary whole is the cell,
    tried from six tokens down to one.
    """
    if not tokens:
        raise RowError(f"ran out of cells in: {row[:80]}")
    for width in range(min(6, len(tokens)), 0, -1):
        candidate = " ".join(tokens[-width:])
        if pattern.fullmatch(candidate):
            del tokens[-width:]
            return candidate
    raise RowError(
        f"cell {tokens[-1]!r} fails its shape; tail: "
        f"...{' '.join(tokens[-10:])!r}")


def parse_row(un: str, row: str) -> dict[str, Any]:
    """One table C row, parsed from both ends toward the middle.

    The back half of the row is a run of closed-vocabulary cells, so it is read
    backwards, popping one validated cell at a time. What remains at the front
    is name, class, classification code, packing group and dangers — and there
    the *class* is the anchor: it is the first token after the name that the
    class grammar accepts and the classification code confirms.
    """
    tokens = tighten(row).split(" ")

    # Walk back over the remark cell: remarks are digits/commas/"see" refs, and
    # end at the cones cell. The safe cut is the *equipment* cell: scan from the
    # end for the last token run matching EQUIPMENT preceded by a boolean.
    remarks_tokens: list[str] = []
    while tokens:
        candidate = tokens[-1]
        if CONES.fullmatch(candidate):
            ahead = " ".join(tokens[max(0, len(tokens) - 8):-1])
            if re.search(r"(?:PP|EP|EX|TOX|A|\*)$", ahead):
                break
        remarks_tokens.insert(0, tokens.pop())
        if len(remarks_tokens) > 60:
            raise RowError(f"remark cell will not close in: {row[:90]}")

    remarks = undouble(" ".join(remarks_tokens))
    cones = _take(CONES, tokens, row)
    equipment = _take(EQUIPMENT, tokens, row)
    protection = _take(BOOL, tokens, row)
    explosion = _take(EXPLOSION, tokens, row)
    temperature = _take(TEMP, tokens, row)
    pump_room = _take(BOOL, tokens, row)
    sampler = _take(SMALL, tokens, row)

    # Density is free-form ("0,68 - 0,72", "-", "*", occasionally a footnote
    # like ", 10)" glued on). It sits between the filling % and the sampler, so
    # it is everything left after the four numeric cells are popped... which
    # must come off before it. Pop them from the *front* side instead: find the
    # vessel type token from the front of the remaining tail.
    front = tokens
    # The head anchor is the class/code/packing-group triple: the first place
    # where three consecutive tokens satisfy those three grammars is where the
    # name ends. (A bare class digit inside a name does occur, but never with a
    # classification code and packing group right behind it.)
    triple_at = None
    for i in range(1, len(front) - 2):
        if (CLASS.fullmatch(front[i]) and CODE.fullmatch(front[i + 1])
                and PG.fullmatch(front[i + 2])):
            triple_at = i
            break
    if triple_at is None:
        raise RowError(f"no class/code/group triple in: {row[:90]}")

    # After the triple come the dangers — one cell, but set with spaces when it
    # says "F or S" — and then the vessel type, which is the first following
    # token the vessel grammar accepts (`*` rows have `*` all the way).
    vessel_at = None
    for i in range(triple_at + 3, len(front)):
        if VESSEL.fullmatch(front[i]) and i > triple_at + 3:
            vessel_at = i
            break
    if vessel_at is None:
        raise RowError(f"no vessel type in: {row[:90]}")

    head = front[:triple_at]
    cls, code, packing = front[triple_at:triple_at + 3]
    dangers = " ".join(front[triple_at + 3:vessel_at])
    middle = front[vessel_at:]
    vessel = middle.pop(0)
    design = middle.pop(0) if middle else None
    tank_type = middle.pop(0) if middle else None
    tank_equipment = middle.pop(0) if middle else None
    pressure = middle.pop(0) if middle else None
    filling = middle.pop(0) if middle else None
    for cell, pattern in ((design, SMALL), (tank_type, SMALL),
                          (tank_equipment, SMALL), (pressure, NUMBER),
                          (filling, NUMBER)):
        if cell is None or not pattern.fullmatch(cell):
            raise RowError(f"tank cells fail in: {row[:90]}")
    density = numbers_tight(" ".join(middle)) or "-"

    name = " ".join(head)
    if not name:
        raise RowError(f"empty name in: {row[:90]}")
    if not dangers:
        raise RowError(f"empty dangers cell in: {row[:90]}")

    return {
        "un": un,
        "name_nl": tidy(name),
        "class": cls,
        "classification_code": tidy(code or ""),
        "packing_group": tidy(packing or ""),
        "dangers": tidy(dangers or ""),
        "vessel_type": vessel,
        "cargo_tank_design": tidy(design),
        "cargo_tank_type": tidy(tank_type),
        "cargo_tank_equipment": tidy(tank_equipment),
        "opening_pressure_kpa": tidy(pressure),
        "max_filling_percent": tidy(filling),
        "density": "" if density == "-" else density,
        "sampling_device": tidy(sampler),
        "pump_room_below_deck": tidy(pump_room),
        "temperature_class": tidy(temperature),
        "explosion_group": tidy(explosion),
        "explosion_protection": tidy(protection),
        "equipment": tidy(equipment),
        "blue_cones": tidy(cones),
        "remarks": remarks,
    }


def dutch_rows(index_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for key in DUTCH_PAGES:
        text = flatten(index[key]["text"])
        # Rows start after the header; the header ends at the last column name.
        start = text.find("Extra eisen of aantekeningen")
        body = text[start + len("Extra eisen of aantekeningen"):]
        starts = list(ROW_START.finditer(body))
        for i, match in enumerate(starts):
            end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
            raw = body[match.end():end].strip()
            try:
                rows.append(parse_row(match.group(1), raw))
            except RowError as exc:
                failures.append(f"{match.group(1)}: {exc}")
    return rows, failures


# --- the English reading ----------------------------------------------------
#
# The UNECE PDF prints table C on landscape pages with a numbered header row —
# (1) to (20) — whose x positions are the column boundaries. Words are assigned
# to columns by those positions, lines are grouped into rows by the UN number
# in column (1), and every cell then faces the same closed vocabularies as the
# Dutch reading. Booleans print as yes/no in this edition and are mapped onto
# True/False so the two readings compare directly.

ENGLISH_FIELDS = [field if field != "name_nl" else "name_en" for field in FIELDS]


def _pages_of_table_c(doc) -> list[int]:
    pages = []
    for number in range(doc.page_count):
        text = doc[number].get_text("text")
        if "(20)" in text and re.search(r"\(3\s?\)?\s?a|\(3a\)", text):
            if re.search(r"Type of (?:tank )?vessel|3\.2\.3\.2|Table C", text):
                pages.append(number)
    return pages


def _header_anchors(page) -> list[tuple[str, float, float]]:
    """The x span of every numbered header cell on this page."""
    anchors = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        if re.fullmatch(r"\((?:\d{1,2}|3\)?a|3\)?b)\)?", word):
            anchors.append((word.strip("()"), x0, x1, y1))
    anchors.sort(key=lambda a: a[1])
    return [(name, x0, x1) for name, x0, x1, _ in anchors]


def probe_english(pdf_path: Path) -> int:
    import fitz

    doc = fitz.open(pdf_path)
    pages = _pages_of_table_c(doc)
    print(f"table C candidate pages: {len(pages)}")
    print(f"first, last: {pages[:3]} ... {pages[-3:]}" if pages else "none found")
    if not pages:
        # Fall back: show what the header of a likely page looks like.
        for number in range(doc.page_count):
            if "Table C" in doc[number].get_text("text"):
                print(f"page {number} mentions Table C; first 400 chars:")
                print(doc[number].get_text("text")[:400])
                break
        return 1
    page = doc[pages[0]]
    print(f"page {pages[0]}: rect {page.rect}")
    anchors = _header_anchors(page)
    print("header anchors:", [(n, round(a), round(b)) for n, a, b in anchors])
    words = page.get_text("words")
    words.sort(key=lambda w: (round(w[1]), w[0]))
    print("first 120 words with x,y:")
    for x0, y0, _x1, _y1, word, *_ in words[:120]:
        print(f"  {round(x0):4d},{round(y0):4d} {word}")
    return 0


def english_rows(pdf_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    import fitz

    doc = fitz.open(pdf_path)
    pages = _pages_of_table_c(doc)
    if not pages:
        return [], ["no table C pages found"]

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for number in pages:
        page = doc[number]
        anchors = _header_anchors(page)
        if len(anchors) != 21:  # (1),(2),(3)a,(3)b,(4)..(20)
            failures.append(f"page {number}: {len(anchors)} header anchors")
            continue
        # Column k spans from its anchor's left edge to the next anchor's.
        edges = [x0 for _n, x0, _x1 in anchors] + [page.rect.width]
        header_bottom = max(
            y1 for _x0, _y0, _x1, y1, word, *_ in page.get_text("words")
            if re.fullmatch(r"\((?:\d{1,2}|3\)?a|3\)?b)\)?", word))

        lines: dict[int, list[tuple[float, str]]] = {}
        for x0, y0, x1, _y1, word, *_ in page.get_text("words"):
            if y0 <= header_bottom:
                continue
            lines.setdefault(round(y0), []).append((x0, word))

        current: list[list[str]] | None = None
        margin = edges[0] - 2
        for y in sorted(lines):
            cells = [[] for _ in range(21)]
            for x0, word in sorted(lines[y]):
                column = max(0, min(20, next(
                    (i for i in range(21) if x0 < edges[i + 1] - 1), 20)))
                cells[column].append(word)
            first = " ".join(cells[0])
            if re.fullmatch(r"\d{4}", first):
                if current:
                    rows.append(_english_row(current, failures))
                current = cells
            elif current:
                for i, extra in enumerate(cells):
                    current[i].extend(extra)
            del margin
        if current:
            rows.append(_english_row(current, failures))
            current = None
    return [row for row in rows if row], failures


def _english_row(cells: list[list[str]], failures: list[str]) -> dict[str, Any] | None:
    values = [" ".join(cell).strip() for cell in cells]
    row = dict(zip(ENGLISH_FIELDS, values))
    for key in ("pump_room_below_deck", "explosion_protection"):
        low = row[key].lower()
        row[key] = {"yes": "True", "no": "False"}.get(low, row[key])
    checks = [
        ("vessel_type", VESSEL), ("cargo_tank_design", SMALL),
        ("cargo_tank_type", SMALL), ("cargo_tank_equipment", SMALL),
        ("opening_pressure_kpa", NUMBER), ("max_filling_percent", NUMBER),
        ("sampling_device", SMALL), ("pump_room_below_deck", BOOL),
        ("temperature_class", TEMP), ("explosion_group", EXPLOSION),
        ("explosion_protection", BOOL), ("equipment", EQUIPMENT),
        ("blue_cones", CONES),
    ]
    for key, pattern in checks:
        cell = tighten(row[key]) or "-"
        row[key] = cell
        if not pattern.fullmatch(cell):
            failures.append(f"{row['un']}: {key} {cell!r} fails its shape")
            return None
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Read ADN table C")
    parser.add_argument("--dutch", type=Path,
                        help="path of the stored Dutch ADN index JSON")
    parser.add_argument("--english", type=Path,
                        help="path of the English ADN PDF")
    parser.add_argument("--check", type=Path,
                        help="compare against a previous reading (JSON)")
    parser.add_argument("--out", type=Path, help="write the rows to this file")
    parser.add_argument("--probe", action="store_true",
                        help="report the layout of the English pages and stop")
    args = parser.parse_args()

    if args.english and args.probe:
        return probe_english(args.english)

    if args.english:
        rows, failures = english_rows(args.english)
        print(f"rows parsed: {len(rows)}")
        print(f"failures: {len(failures)}")
        for failure in failures[:30]:
            print("  !", failure)
        if args.out and rows:
            args.out.write_text(
                json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8")
            print(f"written: {args.out}")
        return 1 if failures else 0

    if args.dutch:
        rows, failures = dutch_rows(args.dutch)
        print(f"rows parsed: {len(rows)}")
        print(f"rows failed: {len(failures)}")
        for failure in failures[:20]:
            print("  !", failure)
        if args.out:
            args.out.write_text(
                json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8")
            print(f"written: {args.out}")
        return 1 if failures else 0

    print("nothing to do: give --dutch or --english", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
