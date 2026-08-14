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
#: Nine table C names begin with a lower-case prefix — n-PROPANOL,
#: sec-BUTYL CHLORIDE and their kind — and the table A rule of "a capital
#: begins a name" silently fed those rows into their predecessor's remark
#: cell. The lower-case branch demands the hyphenated shape so that prose
#: inside a cell ("met ten hoogste") still does not pass.
ROW_START = re.compile(
    r"(?:^|(?<= ))(\d{4}) (?=[A-Z“(]|\d\S*[A-Za-z]|[a-z][A-Za-z]*-[A-Z])")

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

    # The export writes the cells of columns (7) and (9) in each other's
    # place, against its own header. Measured, not assumed: of the English
    # rows blocked on exactly this pair, 362 match the Dutch perfectly once
    # the two are swapped, and every row that matched *without* the swap has
    # design equal to equipment, where a swap cannot show. The English
    # assignment is verified against its own printed band labels, and the
    # physics sides with it — anhydrous ammonia requires pressure cargo tank
    # design 1, which the unswapped export would deny. One more entry in the
    # export's damage record, alongside the 7.1.4.3.4 matrix.
    design, tank_equipment = tank_equipment, design

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
# The UNECE PDF prints table C *transposed*: portrait pages on which the twenty
# column numbers run down the left edge — (20) at the top, (1) at the bottom —
# each opening a horizontal band, while the substances stand side by side as up
# to eight page-columns. The probe run measured it: markers at x≈165, provision
# references beside them at x≈178, and the substance columns from x≈198. A cell
# is the intersection of its attribute band and its substance column, wrapped
# over several lines, so words are gathered per (band, column) and joined in
# reading order. Booleans print as yes/no and are mapped onto True/False so the
# two readings compare directly.

ENGLISH_FIELDS = [field if field != "name_nl" else "name_en" for field in FIELDS]

#: Band markers sit in a narrow x window at the left edge; anything to the left
#: of the first substance column is label or provision text, not a value.
MARKER_X = (150.0, 195.0)
MARKER = re.compile(r"\(\d{1,2}\)|\(3[ab]\)")

#: The order the markers carry down the page maps onto the seed fields.
BAND_FIELDS = {
    "1": "un", "2": "name_en", "3a": "class", "3b": "classification_code",
    "4": "packing_group", "5": "dangers", "6": "vessel_type",
    "7": "cargo_tank_design", "8": "cargo_tank_type",
    "9": "cargo_tank_equipment", "10": "opening_pressure_kpa",
    "11": "max_filling_percent", "12": "density", "13": "sampling_device",
    "14": "pump_room_below_deck", "15": "temperature_class",
    "16": "explosion_group", "17": "explosion_protection", "18": "equipment",
    "19": "blue_cones", "20": "remarks",
}


def _bands(page) -> list[tuple[str, float]]:
    """The column-number markers down the left edge, top to bottom."""
    found = []
    for x0, y0, _x1, y1, word, *_ in page.get_text("words"):
        if MARKER_X[0] <= x0 <= MARKER_X[1] and MARKER.fullmatch(word):
            found.append((word.strip("()"), (y0 + y1) / 2))
    found.sort(key=lambda item: item[1])
    return found


def probe_english(pdf_path: Path) -> int:
    import fitz

    doc = fitz.open(pdf_path)
    pages = _pages_of_table_c(doc)
    print(f"table C candidate pages: {len(pages)}")
    print(f"first, last: {pages[:3]} ... {pages[-3:]}" if pages else "none")
    if not pages:
        return 1
    page = doc[pages[0]]
    print(f"page {pages[0]}: rect {page.rect}")
    print("marker column, x 140-200, every word:")
    for x0, y0, _x1, _y1, word, *_ in sorted(page.get_text("words"),
                                             key=lambda w: (w[1], w[0])):
        if 140 <= x0 <= 200:
            print(f"  {round(x0):4d},{round(y0):4d} {word!r}")
    print("bottom stripe, y 560-800, x > 195:")
    for x0, y0, _x1, _y1, word, *_ in sorted(page.get_text("words"),
                                             key=lambda w: (w[1], w[0])):
        if y0 > 560 and x0 > 195:
            print(f"  {round(x0):4d},{round(y0):4d} {word!r}")
    return 0


def _pages_of_table_c(doc) -> list[int]:
    pages = []
    for number in range(doc.page_count):
        text = doc[number].get_text("text")
        if "(20)" in text and "(14)" in text and "(1)" in text:
            # "Tableau C" for the French edition; the section number is the
            # same in every language and carries the page on its own.
            if "Table C" in text or "Tableau C" in text or "3.2.3" in text:
                pages.append(number)
    return pages


def english_rows(pdf_path: Path,
                 language: str = "en") -> tuple[list[dict[str, Any]], list[str]]:
    import fitz

    doc = fitz.open(pdf_path)
    pages = _pages_of_table_c(doc)
    if not pages:
        return [], ["no table C pages found"]

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    per_page: list[tuple[int, int]] = []
    for number in pages:
        page = doc[number]
        bands = _bands(page)
        names = [name for name, _y in bands]
        if sorted(names, key=lambda n: BAND_ORDER[n]) != ORDERED or len(names) != 21:
            failures.append(f"page {number}: bands {names}")
            continue

        # A value sits centred on its marker's height, so a band runs from the
        # midpoint above its marker to the midpoint below. The markers come
        # (20) first: the page prints the table's columns in reverse.
        centres = [y for _n, y in bands]
        # The page's copyright line sits above the table; the first band opens
        # half a band-width above its own marker, not at the page top.
        top = centres[0] - (centres[1] - centres[0]) / 2
        mids = [top] + [(a + b) / 2 for a, b in zip(centres, centres[1:])] + [790.0]
        spans = {name: (mids[i], mids[i + 1])
                 for i, (name, _y) in enumerate(bands)}

        # The page footer sits under the (1) band and is no substance.
        words = [
            w for w in page.get_text("words")
            if w[0] > MARKER_X[1] and (w[1] + w[3]) / 2 < 790.0
            and not re.fullmatch(r"-\s*\d+\s*-", w[4])]

        # The substance columns come from the UN band itself: every four-digit
        # number in it anchors one column, and cells are left-aligned on it.
        top_1, bottom_1 = spans["1"]
        top, bottom = top_1, bottom_1
        anchors = sorted(
            w[0] for w in words
            if top <= (w[1] + w[3]) / 2 < bottom and re.fullmatch(r"\d{4}", w[4]))
        if not anchors:
            failures.append(f"page {number}: no UN anchors")
            continue

        def column_of(x0: float) -> int | None:
            # Cells are left-aligned on their UN number — almost. Page 205
            # prints UN 1148 five points right of its own column's values, so
            # the window opens eight points left of the anchor: wide enough for
            # that indent, narrow enough that a neighbour's wrapped line (which
            # shifts about nine points per line) rarely reaches it.
            if x0 < anchors[0] - 8:
                return None
            for i in range(len(anchors) - 1, -1, -1):
                if x0 >= anchors[i] - 8:
                    return i
            return None

        cells: dict[tuple[str, int], list[tuple[float, float, str]]] = {}
        for x0, y0, _x1, y1, word, *_ in words:
            centre = (y0 + y1) / 2
            band = next(
                (n for n, (a, b) in spans.items() if a <= centre < b), None)
            column = column_of(x0)
            if band is None or column is None:
                continue
            cells.setdefault((band, column), []).append((x0, centre, word))

        marker_y = dict(bands)

        def read(got: list[tuple[float, float, str]]) -> str:
            # The table is printed rotated: a cell's words run bottom-up, and
            # its lines stack left to right. Reading order is therefore by x
            # first and by *descending* y within the line.
            return " ".join(w for _x, _y, w in
                            sorted(got, key=lambda item: (item[0], -item[1])))

        for column in range(len(anchors)):
            values: dict[str, str] = {}
            problems: list[str] = []

            # A long rotated name reaches down past the midpoint into the (1)
            # band, and a long remark reaches down into the (19) band. So those
            # band pairs are pooled, and the single-token cell is the token of
            # its own shape nearest its marker; everything else in the pool is
            # the neighbour's text.
            pool = cells.get(("1", column), [])
            un_words = [item for item in pool if re.fullmatch(r"\d{4}", item[2])]
            if len(un_words) != 1:
                failures.append(
                    f"page {number} column {column}: "
                    f"{len(un_words)} UN numbers in {read(pool)!r}")
                continue
            values["un"] = un_words[0][2]
            name_low = [w for w in pool if w is not un_words[0]]

            pool = (cells.get(("2", column), [])
                    + cells.get(("3a", column), [])
                    + cells.get(("3b", column), []))
            cls = [item for item in pool
                   if CLASS.fullmatch(item[2])
                   and abs(item[1] - marker_y["3a"]) <= 8]
            code = [item for item in pool
                    if item[2] not in {i[2] for i in cls} or item not in cls]
            code = [item for item in pool
                    if item is not (cls[0] if cls else None)
                    and CODE.fullmatch(item[2])
                    and abs(item[1] - marker_y["3b"]) <= 8]
            chosen_class = min(
                cls, key=lambda i: abs(i[1] - marker_y["3a"])) if cls else None
            chosen_code = min(
                code, key=lambda i: abs(i[1] - marker_y["3b"])) if code else None
            values["class"] = chosen_class[2] if chosen_class else "-"
            values["classification_code"] = chosen_code[2] if chosen_code else "-"
            name_extra = [item for item in pool
                          if item is not chosen_class and item is not chosen_code]

            pool = cells.get(("19", column), []) + cells.get(("20", column), [])
            near = sorted(
                (item for item in pool
                 if re.fullmatch(r"[012*\-]", item[2])
                 and abs(item[1] - marker_y["19"]) <= 8),
                key=lambda item: abs(item[1] - marker_y["19"]))
            if len(near) > 1:
                # Equidistant from the marker: the cones digit stands on the
                # cell's first rotated line, remark numbers wrap onto later
                # lines further right — the leftmost candidate is the cell.
                near.sort(key=lambda item: item[0])
            chosen = near[0] if near else None
            values["blue_cones"] = chosen[2] if chosen else "-"
            values["remarks"] = read(
                [w for w in pool if w is not chosen])

            values["name_en"] = read(name_extra + name_low)

            for band, field in BAND_FIELDS.items():
                if band in ("1", "2", "3a", "3b", "19", "20"):
                    continue
                values[field] = read(cells.get((band, column), []))
            del problems

            # A substance that continues onto the next page repeats its UN
            # number above an otherwise empty column. That is a continuation
            # head, not a row.
            if not any(values[f] for f in ENGLISH_FIELDS
                       if f not in ("un", "name_en", "remarks")):
                print(f"    continuation column skipped: page {number}, "
                      f"UN {values['un']}, name {values['name_en']!r}, "
                      f"remarks {values['remarks']!r}")
                continue
            row = _english_row(values, failures)
            if row:
                rows.append(row)
        per_page.append((number, len(anchors)))
        strays = [w[4] for w in words
                  if top_1 <= (w[1] + w[3]) / 2 < bottom_1
                  and not re.fullmatch(r"\d{4}", w[4])]
        print(f"page {number}: uns "
              + " ".join(w[4] for w in sorted(
                  (w for w in words
                   if top_1 <= (w[1] + w[3]) / 2 < bottom_1
                   and re.fullmatch(r"\d{4}", w[4])), key=lambda w: w[0]))
              + (f" | strays {strays}" if strays else ""))
    print("pages and column counts:", per_page)
    from collections import Counter
    print("UN multiset:", sorted(Counter(r["un"] for r in rows).items()))
    if language != "en":
        # The geometry is the same in either authentic language; only the name
        # column speaks a different one, and it is named for what it holds.
        for row in rows:
            row[f"name_{language}"] = row.pop("name_en")
    return rows, failures


BAND_ORDER = {"1": 1, "2": 2, "3a": 3, "3b": 4, **{str(n): n + 2 for n in range(4, 21)}}
# The transposed page prints (3a) and (3b) with the letter inside the bracket.

ORDERED = sorted(BAND_FIELDS, key=lambda n: BAND_ORDER[n])


def _english_row(values: dict[str, str], failures: list[str]) -> dict[str, Any] | None:
    row = dict(values)
    if not re.fullmatch(r"\d{4}", row.get("un", "")):
        failures.append(f"un {row.get('un')!r} is no UN number")
        return None
    for key in ("pump_room_below_deck", "explosion_protection"):
        low = row[key].strip().lower()
        # The English edition prints yes/no, the French oui/non; the seed holds
        # the boolean either way.
        row[key] = {"yes": "True", "oui": "True",
                    "no": "False", "non": "False"}.get(low, row[key])
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
            failures.append(
                f"{row['un']}: {key} {cell!r} fails its shape; row: "
                + " | ".join(f"{k}={row.get(k, '')!r}" for k in
                             ("un", "vessel_type", "cargo_tank_design",
                              "cargo_tank_type", "opening_pressure_kpa",
                              "max_filling_percent", "blue_cones", "remarks")))
            return None
    return row


# --- the comparison ---------------------------------------------------------
#
# The two readings do not agree row for row by design: where the book names a
# substance "PETROLEUM DISTILLATES, N.O.S. or PETROLEUM PRODUCTS, N.O.S." the
# English edition prints one row and the Dutch export prints one row per
# alternative name with identical cells. So the English reading is the row
# set, and every English row must be matched by at least one Dutch row on all
# comparable cells — names aside — while every Dutch row must find exactly one
# English home. Dutch rows the export provably lacks (its known damage) leave
# English rows with a single reading, and the seed says so per row.

COMPARED = [
    "class", "classification_code", "packing_group", "dangers", "vessel_type",
    "cargo_tank_design", "cargo_tank_type", "cargo_tank_equipment",
    "opening_pressure_kpa", "max_filling_percent", "density",
    "sampling_device", "pump_room_below_deck", "temperature_class",
    "explosion_group", "explosion_protection", "equipment", "blue_cones",
]


def _norm(field: str, value: str) -> str:
    value = (value or "").strip().replace("–", "-")
    if value in ("-", ""):
        return ""
    if field == "dangers":
        # The English cell wraps mid-token ("2." / "1+N1"), so spaces go
        # first; and the export prints "2, 1" where the book prints "2.1".
        packed = re.sub(r"\s+", "", value.upper())
        packed = re.sub(r"(\d),(\d)", r"\1.\2", packed)
        tokens = sorted(t.rstrip(".") for t in re.split(r"[+(),]+", packed) if t)
        return "+".join(tokens)
    if field == "equipment":
        # The rotated English cell wraps over lines whose reading order the
        # geometry cannot always settle; the codes are a set either way.
        return ",".join(sorted(re.findall(r"PP|EP|EX|TOX|A(?![A-Z])", value)))
    if field == "explosion_group":
        # Same story with glue: "II B 4) (II B2)" arrives as "II B B24) (II".
        # The alphabet is tiny, so the sorted characters are the comparison.
        return "".join(sorted(re.sub(r"[^0-9A-Z]", "", value.upper())))
    if field == "density":
        value = value.replace(",", ".")
    if field == "remarks":
        numbers = sorted(set(re.findall(r"\d+", value)), key=int)
        see = "see" if "3.2.3.3" in value or "*" in value else ""
        return ",".join(numbers) + see
    return re.sub(r"[\s,]+", "", value.upper())


def _key(row: dict[str, Any]) -> tuple:
    return tuple(_norm(field, row.get(field, "")) for field in COMPARED)


def _diff(a: dict, b: dict) -> list[str]:
    return [f for f in COMPARED if _norm(f, a.get(f, "")) != _norm(f, b.get(f, ""))]


def check_readings(english: list[dict], dutch: list[dict]) -> dict[str, Any]:
    """Pair the readings per UN, best pairs first, and inventory what differs.

    Variant families make greedy first-fit treacherous: near-identical rows
    differ in one late column, and pairing the wrong twins manufactures two
    disagreements out of none. So within each UN every English row is scored
    against every free Dutch row, the globally closest pair binds first, and a
    second Dutch row may join an English one only when it matches exactly —
    that is the export's or-name split, two rows for one printed row.
    """
    from collections import defaultdict

    by_un_en: dict[str, list[dict]] = defaultdict(list)
    by_un_nl: dict[str, list[dict]] = defaultdict(list)
    for row in english:
        by_un_en[row["un"]].append(row)
    for row in dutch:
        by_un_nl[row["un"]].append(row)

    matched, disagreements, single = [], [], []
    unmatched_dutch: list[dict] = []
    for un in sorted(set(by_un_en) | set(by_un_nl)):
        en_rows = [dict(r) for r in by_un_en.get(un, [])]
        nl_rows = list(by_un_nl.get(un, []))
        scored = sorted(
            (len(_diff(e, d)), ei, di)
            for ei, e in enumerate(en_rows)
            for di, d in enumerate(nl_rows))
        taken_e: dict[int, dict] = {}
        taken_d: set[int] = set()
        partners: dict[int, list[dict]] = defaultdict(list)
        for score, ei, di in scored:
            if di in taken_d:
                continue
            if ei in taken_e:
                # A second Dutch row joins only as an exact or-split twin.
                if score == 0:
                    partners[ei].append(nl_rows[di])
                    taken_d.add(di)
                continue
            if score > 4:
                continue
            taken_e[ei] = nl_rows[di]
            partners[ei].append(nl_rows[di])
            taken_d.add(di)
        for ei, row in enumerate(en_rows):
            if ei not in taken_e:
                row["readings"] = 1
                single.append(row)
                continue
            twins = partners[ei]
            row["name_nl"] = " / ".join(
                dict.fromkeys(p["name_nl"] for p in twins))
            row["readings"] = 2
            fields = _diff(row, taken_e[ei])
            if fields:
                # The dispute is attached here, on the pairing itself: tagging
                # rows afterwards by value-lookalike marked innocent variant
                # twins as disputed too.
                row["disputed"] = {
                    f: {"en": row.get(f, ""), "nl": taken_e[ei].get(f, "")}
                    for f in fields}
                disagreements.append({
                    "un": un, "fields": fields,
                    "english": {f: row.get(f, "") for f in fields},
                    "dutch": {f: taken_e[ei].get(f, "") for f in fields},
                })
            matched.append((row, twins))
        unmatched_dutch.extend(
            d for di, d in enumerate(nl_rows) if di not in taken_d)

    return {
        "matched": matched,
        "single": single,
        "disagreements": disagreements,
        "unmatched_dutch": unmatched_dutch,
    }


def emit_seed(english: list[dict], dutch: list[dict], out: Path) -> dict:
    """Write the seed from the paired readings.

    Every row carries the English cells — the UNECE edition is the complete
    print and its band layout is verified against its own labels — with the
    Dutch name(s) joined on. `readings` says how many independent readings
    stand behind the row; where the two disagree on a cell the row keeps both
    under `disputed` and the application must treat that field as not settled.
    Nothing is averaged and nothing is discarded silently.
    """
    outcome = check_readings(english, dutch)
    entries = [row for row, _twins in outcome["matched"]]
    for row in outcome["single"]:
        row = dict(row)
        row["name_nl"] = ""
        entries.append(row)
    entries.sort(key=lambda r: (r["un"], r.get("name_en", "")))
    seed = {
        "_comment": (
            "Table C of chapter 3.2 of the ADN — the substances admitted to "
            "carriage in tank vessels — read twice: geometrically from the "
            "UNECE English ADN 2025 PDF (the row set and every cell) and from "
            "the official Dutch edition's list pages (the corroboration and "
            "the Dutch names). A compilation of facts offered as an aid; the "
            "published text of the ADN remains authoritative."),
        "edition": "ADN 2025, in force 1 January 2025",
        "source": (
            "English reading: UNECE ADN 2025 (sources.json id adn), table C "
            "pages read by band and column with scripts/extract_adn_table_c.py. "
            "Dutch reading: the mindef.nl HTML export (id adn_nl_index), five "
            "ADNC list pages."),
        "cross_check": {
            "rows_english": len(english),
            "rows_dutch": len(dutch),
            "rows": len(entries),
            "settled_rows": len(outcome["matched"]) - len(outcome["disagreements"]),
            "rows_with_disputed_cells": len(outcome["disagreements"]),
            "rows_read_once": len(outcome["single"]),
            "dutch_rows_unplaced": len(outcome["unmatched_dutch"]),
            "note": (
                "The Dutch export splits a printed row per alternative name "
                "(52 rows for the 26 printed rows of UN 1268), swaps the data "
                "cells of columns (7) and (9) against its own header, omits "
                "UN 1977 and UN 1999 entirely along with single variant rows "
                "of several N.O.S. entries, and glues its remark column four "
                "languages deep. Each was measured during the comparison; "
                "rows the export lacks carry readings 1, and a cell the two "
                "readings give differently is kept under `disputed` with both "
                "values — such a cell is not settled and must not be "
                "presented as an answer."),
        },
        "entries": entries,
    }
    out.write_text(json.dumps(seed, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description="Read ADN table C")
    parser.add_argument("--dutch", type=Path,
                        help="path of the stored Dutch ADN index JSON")
    parser.add_argument("--english", type=Path,
                        help="path of a UNECE ADN PDF, read geometrically")
    parser.add_argument("--language", default="en", choices=["en", "fr"],
                        help="which authentic language that PDF is in; the "
                             "name column is stored as name_<language>")
    parser.add_argument("--check", type=Path,
                        help="compare against a previous reading (JSON)")
    parser.add_argument("--out", type=Path, help="write the rows to this file")
    parser.add_argument("--probe", action="store_true",
                        help="report the layout of the English pages and stop")
    parser.add_argument("--dump", action="store_true",
                        help="print every row to the log, one JSON per line")
    parser.add_argument("--probe-page", type=int, default=None,
                        help="dump every word of one PDF page with coordinates")
    parser.add_argument("--emit", nargs=3, metavar=("ENGLISH", "DUTCH", "SEED"),
                        help="pair the two readings (JSON files) and write the seed")
    args = parser.parse_args()

    if args.emit:
        english = json.loads(Path(args.emit[0]).read_text(encoding="utf-8"))
        dutch = json.loads(Path(args.emit[1]).read_text(encoding="utf-8"))
        outcome = emit_seed(english, dutch, Path(args.emit[2]))
        print(f"seed written: {args.emit[2]}")
        print(f"  matched: {len(outcome['matched'])}, of which disputed: "
              f"{len(outcome['disagreements'])}")
        print(f"  single-reading rows: {len(outcome['single'])}")
        print(f"  dutch rows unplaced: {len(outcome['unmatched_dutch'])}")
        for row in outcome["unmatched_dutch"]:
            print(f"    unplaced: {row['un']} {row['name_nl'][:60]}")
        return 0

    if args.english and args.probe_page is not None:
        import fitz
        page = fitz.open(args.english)[args.probe_page]
        for x0, y0, _x1, y1, word, *_ in sorted(page.get_text("words"),
                                                key=lambda w: (w[0], -w[1])):
            print(f"  {round(x0):4d},{round((y0 + y1) / 2):4d} {word!r}")
        return 0

    if args.english and args.probe:
        return probe_english(args.english)

    if args.english:
        rows, failures = english_rows(args.english, args.language)
        print(f"rows parsed: {len(rows)}")
        print(f"failures: {len(failures)}")
        for failure in failures[:30]:
            print("  !", failure)
        if args.out and rows:
            args.out.write_text(
                json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8")
            print(f"written: {args.out}")
        if args.dump:
            # The development container cannot reach the artifact's blob store,
            # but it can read this log. One row per line, between markers.
            print("=== ROWS BEGIN ===")
            for row in rows:
                print("ROW " + json.dumps(row, ensure_ascii=False))
            print("=== ROWS END ===")
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
