"""Read the whole of table A out of ADR 2025, not just its names.

`extract_adr_names.py` reads column (2). This reads all twenty-three, and the
reason is that the classification table this application computes with is an
**export of ADR 2023**. Since v1.49.0 the manifest has said so, and since
v1.52.0 the eleven rows 2025 added have been carried in by hand in
`adr_2025_additions.json` with the two it withdrew flagged in place. Those are
patches over a foundation that is two years old, and they only cover what was
*added* — not what was changed. Measured against this reading, ADR 2025 changes
a field on 316 of the 2,334 UN numbers the export shares with it. UN 3423
tetramethylammonium hydroxide, solid moved from class 8 to class 6.1: different
labels, different transport category, hazard number 668 instead of 80.

**The book itself does not go into this repository.** What is written down is
the derived table, the same rule `docs/data-sources.md` states for every other
regulatory source. The PDFs stay with whoever holds the licence and are passed
with ``--pdf`` and ``--index``.

## Why two documents are read

The alphabetical index of the same edition is a complete second copy of table A
— all twenty-three columns, sorted by name instead of by UN number, and
therefore typeset independently: 325 pages against 294, different column widths,
different line breaks. A table read by machine does not usually fall over; it
shifts a column, and then two thousand substances quietly carry the wrong value.
Where the two readings agree, the reading is right. Below a threshold nothing is
written at all.

## What is hard about this table

* **There are no column rules.** Nothing is drawn between the columns. Only the
  numbering "(1) (2) (3a) …" in a band above the header gives their positions
  away, and the layout is made anew per page: the name column breathes and
  everything to the right of it shifts with it.
* **The column number is not above the content.** The cells are left-aligned and
  the number is centred over the cell *box*, so a narrow value sits up to
  twenty-three points to the left of the number that names it. The left edges
  are therefore taken from the modes of the word starts, which are sharp because
  a column's cell begins at the same x on every row of the page.
* **A mode can lie.** A name that does not fit wraps, and every continuation
  line shares an indent that is every bit as sharp a mode as a real column. On
  45 pages that indent sits where column (3a) is looked for. So the geometry —
  where each column stands as a fraction of the (3a)…(20) span, which holds to a
  quarter of a point over 282 pages — decides roughly where a column is, the
  page decides exactly, and the busiest mode within ten points of the estimate
  wins. Column (3a) is measured on the class values themselves, which is the one
  thing that column can contain.
* **The unit is the word, except where it cannot be.** A boundary drawn between
  characters cuts a token in half wherever a cell is a shade wider than the
  geometry says: "1 (C5000D" with ")V2" beside it. Right of the class the unit
  is therefore the whole word. Left of it the unit has to be the character,
  because column (1) and column (2) run together in the text layer —
  "1098ALLYLALCOHOL" — and the split is made on the four digits.
* **The UN number is vertically centred.** With a name across three lines it
  stands beside the *second*, so a row is not "text that starts with four
  digits". Every line of the first column is tested, or two substances merge.
* **Two cells can abut with nothing between them.** On the explosives pages the
  tunnel code and the V code of column (16) come out of the text layer as one
  word, "(B1000C)V2". No boundary can separate what the document does not
  separate, so the seam is found on the closing bracket — a V code is the only
  thing that can follow one.

Usage::

    python scripts/extract_adr_table_a.py --pdf ~/adr2025/ADR-2025-NL-Tabel-A.pdf \\
        --index ~/adr2025/ADR-2025-NL-Alfabetische-Index.pdf
    python scripts/extract_adr_table_a.py --pdf … --index … --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SEED = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg"

SOURCE_NAME = ("ADR 2025, Dutch edition — table A of chapter 3.2, with the "
               "alphabetical index of the same edition as a second reading")

#: The column numbers of table A, in the order they stand in.
COLS = ["1", "2", "3a", "3b", "4", "5", "6", "7a", "7b", "8", "9a", "9b", "10",
        "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"]

#: The band with the column numbers; a page showing at least this many has a
#: header that can be read.
MARKERS_NEEDED = 15
MARKER = re.compile(r"^\((\d{1,2}[ab]?)\)$")

#: Everything below this y is the running foot ("ADR 2025 NL   53 / 294").
BODY_BOTTOM = 812.0

#: Where a row begins: four digits, possibly with the name stuck to them.
UN_START = re.compile(r"^\s*(\d{4})\s*")

#: What column (3a) holds: a class or a division, never a word.
CLASS_VALUE = re.compile(r"^\d(\.\d)?[A-Z]?$")

#: Within a row the lines lie 7.1 points apart, 14.2 inside a name; between two
#: rows, 28.3. Measured over the document — there is nothing in between.
ROW_GAP = 21.0

#: Column (15) is "category (tunnel code)" and column (16) holds V codes; on the
#: explosives pages the text layer runs them into one word. The bracket is the
#: seam, and a V code is the only thing that can follow it.
GLUED_15 = re.compile(r"^(.*\))(V\d+.*)$")

#: A cell that is empty is written with a dash in the book.
EMPTY = {"-", "–", "—", ""}

#: The parenthetical additions with which table A tells several rows of one UN
#: number apart. They set the tank and the packing apart, not the substance.
ROW_QUALIFIER = re.compile(
    r"\s*\((?:dampdruk|dampspanning|met een vlampunt)\b[^()]*(?:\([^()]*\)[^()]*)*\)\s*$"
)

#: A hanging hyphen — "verspreidings-, uitstoot- of voortdrijvende lading" — is
#: always followed by one of these. A hyphen at a line break is not.
CONJUNCTION = re.compile(r"^(of|en|dan|noch)\b")


def marker_band(page, ratios: dict[str, float]) -> tuple[float | None, dict[str, float]]:
    """The band with the column numbers, and the centre of each of them.

    A number that the text layer breaks up — "(19)" comes out as "(19" and ")"
    on 32 pages — is put back from where the column stands on the pages that do
    show it, which is stable to well under a point.
    """
    rows: dict[float, dict[str, float]] = defaultdict(dict)
    for x0, y0, x1, _y1, word, *_ in page.get_text("words"):
        found = MARKER.match(word.strip())
        if found:
            rows[round(y0, 1)][found.group(1)] = (x0 + x1) / 2
    band: dict[str, float] | None = None
    top: float | None = None
    for y in sorted(rows):
        if len(rows[y]) >= MARKERS_NEEDED:
            band, top = dict(rows[y]), y
            break
    if band is None:
        return None, {}
    if "3a" in band and "20" in band:
        span = band["20"] - band["3a"]
        for name in COLS:
            if name not in band and name in ratios:
                band[name] = band["3a"] + ratios[name] * span
    return top, band


def learn_marker_ratios(document) -> dict[str, float]:
    """Where each column number stands, as a fraction of the (3a)…(20) span."""
    seen: dict[str, list[float]] = defaultdict(list)
    for index in range(document.page_count):
        top, band = marker_band(document[index], {})
        if top is None or len(band) < len(COLS) or "20" not in band:
            continue
        span = band["20"] - band["3a"]
        for name, centre in band.items():
            seen[name].append((centre - band["3a"]) / span)
    return {name: sorted(v)[len(v) // 2] for name, v in seen.items() if v}


def peak_lefts(page, top: float, centres: dict[str, float]) -> dict[str, float]:
    """A first reading of the cell left edges, from the word starts.

    Good enough to learn the geometry from and not good enough to read with: a
    wrapped name puts a word start where the next column is looked for. This is
    the bootstrap; the median over all pages is the answer.
    """
    hist: Counter = Counter()
    for x0, y0, *_rest in page.get_text("words"):
        if top <= y0 <= BODY_BOTTOM:
            hist[round(x0 * 2) / 2] += 1
    if not hist:
        return {}
    floor = max(2, hist[min(hist)] * 0.5)
    peaks = sorted(x for x, n in hist.items() if n >= floor)
    lefts: dict[str, float] = {}
    previous = -1e9
    for name in COLS:
        if name not in centres:
            continue
        window = [x for x in peaks if previous < x < centres[name]]
        # Column (2) never gets a left of its own — it shares column (1)'s, and
        # the split between them is made on the four digits. Its column number
        # still has to advance the window, or (3a) inherits it and settles on
        # the indent of a wrapped name instead of on the class.
        if window and name != "2":
            lefts[name] = window[0]
        previous = centres[name]
    return lefts


def learn_left_ratios(document, ratios: dict[str, float]) -> dict[str, float]:
    """How far left of its column number each cell begins, as a span fraction.

    The median and not the mean: the pages where a wrapped cell fooled the mode
    are a minority, and a median steps over them where a mean is dragged along.
    """
    seen: dict[str, list[float]] = defaultdict(list)
    for index in range(document.page_count):
        top, centres = marker_band(document[index], ratios)
        if top is None or "3a" not in centres or "20" not in centres:
            continue
        lefts = peak_lefts(document[index], top + 10, centres)
        if len(lefts) < 20:
            continue
        span = centres["20"] - centres["3a"]
        for name, left in lefts.items():
            if name in centres:
                seen[name].append((centres[name] - left) / span)
    return {name: sorted(v)[len(v) // 2] for name, v in seen.items() if v}


def class_left(page, top: float, centre: float) -> float | None:
    """Where column (3a) begins, measured on the class values themselves.

    The other columns can be found from the modes of the word starts. This one
    cannot: the indent of a wrapped name sits inside its window on 45 pages and
    wins, and the tail of the name is then read as the class —
    "PROJECTIELEN inert, met lichtsp" | "oorelement1". What the column can
    *contain* settles it instead.
    """
    lefts = [w[0] for w in page.get_text("words")
             if top <= w[1] <= BODY_BOTTOM and CLASS_VALUE.match(w[4])
             and abs((w[0] + w[2]) / 2 - centre) <= 15]
    return min(lefts) if lefts else None


def cell_lefts(page, top: float, centres: dict[str, float],
               left_ratios: dict[str, float]) -> dict[str, float]:
    """The left edge of every column on this page."""
    hist: Counter = Counter()
    for x0, y0, *_rest in page.get_text("words"):
        if top <= y0 <= BODY_BOTTOM:
            hist[round(x0 * 2) / 2] += 1
    if not hist or "3a" not in centres or "20" not in centres:
        return {}
    floor = max(2, hist[min(hist)] * 0.5)
    peaks = {x: n for x, n in hist.items() if n >= floor}

    span = centres["20"] - centres["3a"]
    lefts: dict[str, float] = {"1": 20.0}
    previous = -1e9
    for name in COLS:
        if name in ("1", "2") or name not in centres or name not in left_ratios:
            continue
        estimate = centres[name] - left_ratios[name] * span
        # The estimate says roughly where the column is; the page says exactly.
        # Two things can be near it: the true left edge, which occurs on every
        # row, and a word start from a wrapped neighbour, which occurs on a few.
        # The busiest wins and distance only breaks a tie. Beyond ten points
        # nothing on the page is believed — that is where the lying modes sit.
        near = [(n, -abs(x - estimate), x) for x, n in peaks.items()
                if previous < x and abs(x - estimate) <= 10.0]
        lefts[name] = max(near)[2] if near else estimate
        previous = centres[name]

    measured = class_left(page, top, centres["3a"])
    if measured is not None:
        lefts["3a"] = measured
    return dict(sorted(lefts.items(), key=lambda item: COLS.index(item[0])))


def columns_of(page, top: float, lefts: dict[str, float]):
    """Every piece of the body text, in the column it belongs to.

    Two units, because the table needs two. Left of the class the unit is the
    character: column (1) and column (2) run together in the text layer. Right
    of it the unit is the whole word, because a boundary drawn between
    characters cuts a token in half wherever a cell is a shade wider than the
    geometry says.
    """
    edges = [(name, lefts[name]) for name in COLS if name in lefts]
    boundary = lefts.get("3a")
    buckets: dict[float, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for block in page.get_text("rawdict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                for char in span["chars"]:
                    x0, y0, x1, _y1 = char["bbox"]
                    if not (top <= y0 <= BODY_BOTTOM):
                        continue
                    if boundary is None or (x0 + x1) / 2 >= boundary:
                        continue
                    buckets[round(y0, 1)]["1"].append((x0, char["c"]))

    right = [(name, left) for name, left in edges if name != "1"]
    for x0, y0, x1, _y1, word, *_ in page.get_text("words"):
        if not (top <= y0 <= BODY_BOTTOM):
            continue
        if boundary is not None and x0 < boundary - 2:
            continue
        for column, piece, at in split_across(word, x0, x1, right):
            buckets[round(y0, 1)][column].append((at, piece))
    return buckets


#: How far a word has to reach past a boundary before it is believed to be two
#: cells run together rather than one cell a shade wider than the geometry says.
STRADDLE = 3.0


def split_across(word: str, x0: float, x1: float,
                 edges: list[tuple[str, float]]):
    """A word, in the column or columns it covers.

    Two cells can abut with nothing between them, and the text layer then hands
    over one word for both: "(B1000C)V2" is the tunnel code and column (16)'s V
    code, "LP101PP67" is a packing instruction and a special packing provision,
    "CV28S1" is a carriage provision and an operation provision. No boundary,
    however well placed, separates what the document does not separate.

    So a word that reaches well past a boundary is cut on it, and the width of
    the characters says where. "Well past" is what keeps this from firing on an
    ordinary cell: the geometry is good to about a point, a real seam is a whole
    token wide, and three points sits between the two. Everything else comes
    back whole, which matters — a boundary drawn through a token destroys both
    the value and the column that receives the crumb.
    """
    covered = [(name, left) for name, left in edges if x0 >= left - 2]
    if not covered:
        return
    start = covered[-1]
    beyond = [(name, left) for name, left in edges
              if left > start[1] and x0 < left - STRADDLE and x1 > left + STRADDLE]
    if not beyond:
        yield start[0], word, x0
        return
    # Cut on the character whose centre crosses the boundary. The width of a
    # word divided over its characters is enough here: the seams are between
    # tokens, not inside them.
    width = (x1 - x0) / len(word) if word else 0.0
    cuts = [0]
    for _name, left in beyond:
        index = max(1, min(len(word) - 1, round((left - x0) / width))) if width else 0
        if index > cuts[-1]:
            cuts.append(index)
    cuts.append(len(word))
    columns = [start] + beyond
    for (name, _left), begin, end in zip(columns, cuts, cuts[1:]):
        piece = word[begin:end]
        if piece:
            yield name, piece, x0 + begin * width


def unglue(row: dict[str, list[str]]) -> None:
    """Take column (16)'s V code back out of column (15)."""
    for index, piece in enumerate(row["15"]):
        found = GLUED_15.match(piece)
        if found:
            row["15"][index] = found.group(1)
            row["16"] = [found.group(2)] + row["16"]


def read_page(page, number: int, ratios: dict[str, float],
              left_ratios: dict[str, float]) -> tuple[list[dict], list[str]]:
    top_marker, centres = marker_band(page, ratios)
    if top_marker is None:
        return [], [f"p{number}: no column numbers found"]
    top = top_marker + 10
    lefts = cell_lefts(page, top, centres, left_ratios)
    if len(lefts) < 20:
        return [], [f"p{number}: only {len(lefts)} columns measured"]

    buckets = columns_of(page, top, lefts)
    bands: list[list[float]] = []
    current: list[float] = []
    previous_y: float | None = None
    for y in sorted(buckets):
        if previous_y is not None and y - previous_y > ROW_GAP:
            bands.append(current)
            current = []
        previous_y = y
        current.append(y)
    if current:
        bands.append(current)

    rows = []
    for band in bands:
        cells: dict[str, list[str]] = defaultdict(list)
        for y in band:
            for column, pieces in buckets[y].items():
                pieces.sort()
                joiner = "" if column == "1" else " "
                text = re.sub(r"\s+", " ", joiner.join(p for _x, p in pieces)).strip()
                if text:
                    cells[column].append(text)
        if not cells:
            continue
        row = {name: cells.get(name, []) for name in COLS}
        unglue(row)
        rows.append(row)
    return rows, []


def read(path: Path) -> tuple[list[dict], list[str]]:
    """Every row of a table A document, in the order it stands in."""
    import fitz

    rows: list[dict] = []
    problems: list[str] = []
    with fitz.open(path) as document:
        ratios = learn_marker_ratios(document)
        left_ratios = learn_left_ratios(document, ratios)
        for index in range(document.page_count):
            page_rows, page_problems = read_page(document[index], index + 1,
                                                 ratios, left_ratios)
            problems.extend(page_problems)
            for row in page_rows:
                # The UN number sits vertically centred in its cell, so with a
                # name across three lines it stands beside the *second*. Testing
                # the block as a whole would call this row a continuation of the
                # one before it and merge two substances without a word.
                if any(UN_START.match(line) for line in row["1"]):
                    row["_page"] = index + 1
                    rows.append(row)
                elif rows:
                    for name in COLS:
                        rows[-1][name] = rows[-1][name] + row[name]
                else:
                    problems.append(f"p{index + 1}: tail row without a predecessor")
    return rows, problems


def join(previous: str, following: str) -> str:
    """Put two lines of one name together.

    A name that does not fit the column breaks after a hyphen, and that hyphen
    belongs to the word: "lithium-" and "ion-polymeer-batterijen" close up. The
    ADR also writes a shared suffix with a hanging hyphen — "verspreidings-,
    uitstoot- of voortdrijvende lading" — and there the space is part of the
    text.
    """
    previous = previous.rstrip()
    following = following.lstrip()
    if (previous.endswith("-") and not previous.endswith(" -")
            and not CONJUNCTION.match(following)):
        return previous + following
    return f"{previous} {following}"


def cell(row: dict, name: str) -> str:
    """One column of one row, as a single value.

    A dash that has arrived against a value is dropped. In this table a dash is
    how an empty cell is written and nothing else, so "P130, LP101-" is a
    packing instruction with the empty cell beside it stuck to its end — the two
    ran together in the text layer and were parted a character too late.
    """
    text = " ".join(row[name]).strip()
    if text in EMPTY:
        return ""
    text = re.sub(r"\s+", " ", text)
    # Per token, not per cell: the empty neighbour can arrive against any of
    # them once the cell wraps, so "P001, R001- IBC03," carries the dash in the
    # middle of the text and at the end of the token it was stuck to. No value
    # in these columns has a hyphen of its own, so a dash that ends a token is
    # always the empty cell next door.
    text = re.sub(r"(?<=[A-Za-z0-9)])[-–—]+(?=[\s,]|$)", "", text)
    return re.sub(r"\s+", " ", text).strip(" ,")


def un_and_name(row: dict) -> tuple[str | None, str]:
    """The UN number and the Dutch name, split off each other."""
    number = None
    name = ""
    for line in row["1"]:
        found = UN_START.match(line)
        if found and number is None:
            number = found.group(1)
            line = UN_START.sub("", line, count=1)
        if line:
            name = join(name, line) if name else line
    previous = None
    while previous != name:
        previous = name
        name = ROW_QUALIFIER.sub("", name).strip()
    return number, name


#: What comes out per row. Columns 9a and 9b — the packing special provisions
#: and the mixed-packing provisions — are read and checked like the rest but are
#: not carried into the seed, because nothing computes with them and a field
#: nobody reads is a field nobody notices going stale.
#:
#: The tank columns (10) to (14) were in that category until v1.65.0 and are not
#: any more. They are what a tank consignment is judged on: whether the substance
#: may travel in a portable tank at all (10), in an ADR tank at all (12), and
#: which vehicle it then requires (14). An empty (12) is not a missing value here
#: — it means the substance is not accepted in an ADR tank, which is a fact worth
#: as much as a code.
FIELDS = {
    "class": "3a",
    "classification_code": "3b",
    "packing_group": "4",
    "labels": "5",
    "special_provisions": "6",
    "limited_quantity": "7a",
    "excepted_quantity": "7b",
    "packing_instructions": "8",
    "portable_tank_instructions": "10",
    "portable_tank_provisions": "11",
    "tank_code": "12",
    "tank_provisions": "13",
    "tank_vehicle": "14",
    "carriage_packages": "16",
    "carriage_bulk": "17",
    "carriage_loading": "18",
    "carriage_operation": "19",
    "hazard_number": "20",
}

CATEGORY = re.compile(r"(?<![\w(])([0-4])(?![\w)])")
TUNNEL = re.compile(r"\(([A-Z0-9/]+)\)")


def entry(row: dict) -> dict[str, Any] | None:
    """One table A row as a record, or None where no UN number was found."""
    number, name = un_and_name(row)
    if number is None:
        return None
    fifteen = " ".join(row["15"]).strip()
    category = CATEGORY.search(fifteen)
    tunnel = TUNNEL.search(fifteen)
    record: dict[str, Any] = {"un": number, "name_nl": name}
    for field, column in FIELDS.items():
        record[field] = cell(row, column)
    record["transport_category"] = category.group(1) if category else ""
    record["tunnel_code"] = tunnel.group(1) if tunnel and tunnel.group(1) != "-" else ""
    record["page"] = row.get("_page")
    return record


def read_entries(path: Path) -> tuple[list[dict], list[str]]:
    rows, problems = read(path)
    entries = [e for e in (entry(row) for row in rows) if e]
    return entries, problems


COMPARED = [f for f in FIELDS if f != "name_nl"] + ["transport_category", "tunnel_code"]


def tokens(value: str) -> frozenset[str]:
    """The codes in a cell, without their order.

    A cell such as column (17) lists provisions, and the two documents lay the
    list out differently: table A puts "AP1" beside "VC1," and the index puts it
    after "VC2,". Reading order then differs while the provisions do not, and it
    is the provisions that are the value. Comparing the text would report a
    disagreement where there is none, and a check that cries wolf is worth
    nothing.
    """
    return frozenset(part for part in re.split(r"[,\s]+", value) if part)


def cross_check(table: list[dict], index: list[dict]) -> dict[str, Any]:
    """Lay the two readings against each other, field by field.

    Per UN number and as a set, because a UN number has several rows and the two
    documents put them in a different order. What is asked is whether the same
    values are there, not whether they are in the same place.
    """
    left: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    right: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for record in table:
        for field in COMPARED:
            left[record["un"]][field].add(tokens(record[field]))
    for record in index:
        for field in COMPARED:
            right[record["un"]][field].add(tokens(record[field]))

    shared = sorted(set(left) & set(right))
    per_field: dict[str, Any] = {}
    for field in COMPARED:
        same = sum(1 for un in shared if left[un][field] == right[un][field])
        examples = [f"UN {un}: table {[sorted(v) for v in left[un][field]]} vs "
                    f"index {[sorted(v) for v in right[un][field]]}"
                    for un in shared if left[un][field] != right[un][field]][:5]
        per_field[field] = {
            "same": same,
            "differs": len(shared) - same,
            "agreement": round(same / len(shared), 4) if shared else None,
            "examples": examples,
        }
    return {
        "un_numbers": {
            "in_both": len(shared),
            "only_in_the_table": sorted(set(left) - set(right))[:20],
            "only_in_the_index": sorted(set(right) - set(left))[:20],
            "agreement": round(len(shared) / len(set(left) | set(right)), 4),
        },
        "fields": per_field,
    }


def fill_from_the_index(table: list[dict], index: list[dict]) -> int:
    """Put back a class the table reading dropped, from the second reading.

    Eight rows come out of table A without a class — a cell that the geometry
    put a hair outside its column. The alphabetical index has them, and using it
    is the point of having read it twice: this is not a value being invented but
    the same value taken from the other document.

    Only where the index is unambiguous. Where it offers a UN number more than
    one class there is a real choice to be made and no basis to make it on, so
    the field stays empty and says so.
    """
    from_index: dict[str, set[str]] = defaultdict(set)
    for record in index:
        if record["class"]:
            from_index[record["un"]].add(record["class"])
    filled = 0
    for record in table:
        if record["class"]:
            continue
        found = from_index.get(record["un"], set())
        if len(found) == 1:
            record["class"] = next(iter(found))
            record["class_from_the_index"] = True
            filled += 1
    return filled


def against_the_export(table: list[dict]) -> dict[str, Any]:
    """What this reading says about the table the application runs on today.

    Not a check on the reading — the export is the older edition, so a
    difference is as likely to be a change as a mistake. It is here to say how
    much of the table 2025 actually moves, which is the reason for reading it.
    """
    try:
        export = json.loads((SEED / "un_numbers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - seed missing
        return {}
    known = {e["un"] for e in export}
    read_uns = {e["un"] for e in table}
    return {
        "in_both": len(known & read_uns),
        "only_in_adr_2025": sorted(read_uns - known),
        "only_in_the_export": sorted(known - read_uns),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True,
                        help="Table A of the Dutch ADR edition")
    parser.add_argument("--index", type=Path, required=True,
                        help="The alphabetical index of the same edition")
    parser.add_argument("--out", type=Path, default=SEED / "adr_table_a.json")
    parser.add_argument("--edition", default="ADR 2025")
    parser.add_argument("--dry-run", action="store_true",
                        help="Read and check, but do not write anything")
    parser.add_argument("--min-agreement", type=float, default=0.97,
                        help="Below this agreement nothing is written")
    args = parser.parse_args(argv)

    table, table_problems = read_entries(args.pdf)
    index, index_problems = read_entries(args.index)
    print(f"table A: {len(table)} rows, "
          f"{len({e['un'] for e in table})} UN numbers")
    print(f"index  : {len(index)} rows, "
          f"{len({e['un'] for e in index})} UN numbers")
    for problem in (table_problems + index_problems)[:10]:
        print("  ", problem)
    if not table:
        print("No rows read.")
        return 1

    checks = cross_check(table, index)
    filled = fill_from_the_index(table, index)
    print("\n--- self-check against the alphabetical index ---")
    print(f"  {filled} empty classes filled from the index")
    print(f"  UN numbers: {checks['un_numbers']['in_both']} in both, "
          f"agreement {checks['un_numbers']['agreement']}")
    for field, result in checks["fields"].items():
        print(f"  {field:24s} {result['same']:5d} same, {result['differs']:4d} "
              f"different, agreement {result['agreement']}")
        for example in result["examples"][:2]:
            print(f"      {example}")

    weakest = min([r["agreement"] for r in checks["fields"].values()
                   if r["agreement"] is not None] or [0])
    if weakest < args.min_agreement:
        print(f"\nAgreement {weakest} is below {args.min_agreement}: the reading "
              "is wrong. Nothing is written.")
        return 1

    moved = against_the_export(table)
    if moved:
        print(f"\nagainst the export the application runs on: "
              f"{moved['in_both']} shared, "
              f"{len(moved['only_in_adr_2025'])} only in ADR 2025, "
              f"{len(moved['only_in_the_export'])} only in the export")

    payload = {
        "_comment": ("Table A of chapter 3.2 of the ADR, read by machine with "
                     "scripts/extract_adr_table_a.py. A compilation of facts "
                     "offered as an aid; the published text of the ADR remains "
                     "authoritative."),
        "edition": args.edition,
        "source": SOURCE_NAME,
        "summary": {
            "rows": len(table),
            "un_numbers": len({e["un"] for e in table}),
            "index_rows": len(index),
            "unreadable_pages": len(table_problems) + len(index_problems),
        },
        "cross_check": checks,
        "classes_filled_from_the_index": filled,
        "against_the_export": moved,
        "entries": sorted(table, key=lambda e: (e["un"], e.get("page") or 0)),
    }
    document = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    print(f"\n{len(table)} rows, {len(document.encode('utf-8'))} bytes")

    if args.dry_run:
        print("Dry run; nothing is written.")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(document, encoding="utf-8")
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover - command line
    raise SystemExit(main())
