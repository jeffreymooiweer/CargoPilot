#!/usr/bin/env python3
"""Read the two tank hierarchies of ADR 4.3 out of the official volumes.

Table A column (12) says which tank code a substance *requires*. It does not
say whether the tank standing on the yard may carry it, and that is the question
a consignor actually has: the vehicle has the code it has. ADR answers it twice,
once for each half of the dangerous goods, and the two answers have nothing in
common but their purpose:

``4.3.3.1.2`` — **gases**, and it is a hierarchy of *codes*. Fifteen rows, each
naming the other codes a substance under that code may also travel in, with the
rule that the pressure figure of the permitted code must be at least the
pressure figure of the required one.

``4.3.4.1.2`` — **classes 3 to 9**, and it is not a hierarchy of codes at all.
It is the rationalized approach: each tank code names the *group of substances*
it is permitted to carry, by class, classification code and packing group, and
inherits the groups of the codes below it. Nothing about the offered code is
compared with the required code; the substance is looked up in the offered
code's group.

Reading them as one thing would be the mistake this file exists to avoid, so
they are read separately and stored separately.

Both are regulatory tables, so both are read twice — the English volume II and
the printed Dutch edition — and a cell the two readings do not agree on is
stored with both values and settles nothing. That is the rule the ADN table C
seed already follows.

Usage::

    python scripts/extract_adr_tank_hierarchy.py --pdf adr2.pdf --language en --probe
    python scripts/extract_adr_tank_hierarchy.py --pdf adr2.pdf --language en --out en.json
    python scripts/extract_adr_tank_hierarchy.py --check en.json nl.json --emit seed.json
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

#: A tank code as the two tables print it: LGAV, L4BN, L1,5BN, S10AN, C*BN.
#: The trailing lower-case letter is a footnote reference set against the code.
TANK_CODE = re.compile(r"[LS](?:[A-Z]{3}|\d+(?:[.,]\d+)?[A-Z]{2})([a-z])?\)?")
GAS_CODE = re.compile(r"[CPR][*#][BCD][NH]")
CLASS = re.compile(r"[1-9](?:\.\d)?")
PACKING_GROUP = re.compile(r"I{1,3}")
#: A classification code of table A column (3b): F1, FT2, ST3, M11, C1, I3, W1.
CLASSIFICATION = re.compile(r"[A-Z]{1,3}\d{0,2}([a-z])?")

#: What each edition calls the two tables, and the sentence that carries the
#: inheritance. The phrases are the edition's own headings; they are how a page
#: is recognised, not text this repository reproduces.
LANGUAGES: dict[str, dict[str, Any]] = {
    "en": {
        "gases_heading": "hierarchy of tanks",
        "gases_column": "other tank code",
        "code_column": "tank code",
        "group_column": "group of permitted substances",
        "class_column": "class",
        "inherit": re.compile(
            r"groups? of permitted substances for tank codes?(.*)", re.IGNORECASE),
        "and": re.compile(r"\band\b", re.IGNORECASE),
    },
    "nl": {
        "gases_heading": "hiërarchie van tanks",
        "gases_column": "andere tankcode",
        "code_column": "tankcode",
        "group_column": "groep van toegestane stoffen",
        "class_column": "klasse",
        "inherit": re.compile(
            r"groepen van de voor de tankcodes?(.*?)toegestane stoffen",
            re.IGNORECASE | re.DOTALL),
        "and": re.compile(r"\ben\b", re.IGNORECASE),
    },
    "de": {
        "gases_heading": "rangordnung der tanks",
        "gases_column": "andere tankcodierung",
        "code_column": "tankcodierung",
        "group_column": "gruppe der zugelassenen stoffe",
        "class_column": "klasse",
        "inherit": re.compile(
            r"gruppen der für die tankcodierungen?(.*?)zugelassenen stoffe",
            re.IGNORECASE | re.DOTALL),
        "and": re.compile(r"\bund\b", re.IGNORECASE),
    },
}


def flatten(text: str) -> str:
    return " ".join(text.split())


def _lines(page, below: float = 0.0) -> list[tuple[float, list[tuple[float, str]]]]:
    """The page's words gathered into lines, each line left to right.

    A line is a band of y, not one exact value: a footnote reference is set
    raised and a wrapped cell sits a point or two off. Four points is the
    tolerance the ADN reader measured for the same typesetting.
    """
    words = [(y0, x0, flatten(word))
             for x0, y0, _x1, _y1, word, *_ in page.get_text("words")
             if y0 > below and word.strip()]
    lines: list[tuple[float, list[tuple[float, str]]]] = []
    for y, x, word in sorted(words):
        if lines and y - lines[-1][0] <= 4.0:
            lines[-1][1].append((x, word))
        else:
            lines.append((y, [(x, word)]))
    return [(y, sorted(items)) for y, items in lines]


def _corridor(page, below: float = 0.0) -> list[tuple[float, float]]:
    """The empty vertical corridors between the columns of this page.

    Measured on the content rather than guessed from the headings: a heading is
    centred over its column and the cells under it are not, so the midpoint
    between two headings falls inside a column often enough to matter. What no
    word covers, over the whole page, is corridor.
    """
    words = [w for w in page.get_text("words") if w[1] > below]
    if not words:
        return []
    left = int(min(w[0] for w in words))
    right = int(max(w[2] for w in words)) + 1
    claimed = bytearray(right - left + 1)
    for x0, _y0, x1, *_ in words:
        for x in range(int(x0) - left, min(int(x1) + 1, right) - left + 1):
            claimed[x] = 1
    corridors: list[tuple[float, float]] = []
    start = None
    for index, taken in enumerate(claimed):
        if taken:
            if start is not None and index - start >= 4:
                corridors.append((start + left, index + left))
            start = None
        elif start is None:
            start = index
    return corridors


def _is_contents(text: str) -> bool:
    return len(re.findall(r"\.{3,}\s*\d+\s*$", text, re.MULTILINE)) >= 4


# --- 4.3.3.1.2, the gases -------------------------------------------------


def gas_pages(doc, language: str) -> list[int]:
    """The pages carrying the hierarchy of tanks for gases.

    One page in every edition read so far, but the count is measured rather
    than assumed: a page qualifies by carrying the heading and enough codes of
    the shape the table is made of.
    """
    words = LANGUAGES[language]
    found = []
    for index in range(doc.page_count):
        text = doc[index].get_text()
        if _is_contents(text):
            continue
        low = text.lower()
        if words["gases_heading"] not in low and words["gases_column"] not in low:
            continue
        if len(GAS_CODE.findall(text)) >= 10:
            found.append(index)
    return found


def gas_rows(doc, pages: list[int]) -> tuple[list[dict[str, Any]], list[str]]:
    """Each required code, and the codes a substance under it may also use.

    The left column holds one code, the right a list of them; both are read off
    the same line. The rows are matched by the line they share and not by the
    order the text comes out of the PDF, which puts the whole left column before
    the whole right one.
    """
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for index in pages:
        page = doc[index]
        for _y, items in _lines(page):
            required = [word for _x, word in items if GAS_CODE.fullmatch(word.strip(","))]
            if not required:
                continue
            head = required[0]
            if "*" not in head:
                # A line of the right-hand column alone, or a note. The row is
                # the line whose first code is the required one.
                continue
            permitted = [word.strip(",") for _x, word in items
                         if GAS_CODE.fullmatch(word.strip(",")) and "#" in word]
            if not permitted:
                failures.append(f"p{index + 1} {head}: no permitted codes on the line")
                continue
            rows.append({"tank_code": head, "also_permitted": permitted})
    return rows, failures


# --- 4.3.4.1.2, the rationalized approach ---------------------------------


def rationalised_pages(doc, language: str) -> list[int]:
    words = LANGUAGES[language]
    found = []
    for index in range(doc.page_count):
        text = doc[index].get_text()
        if _is_contents(text):
            continue
        low = text.lower()
        if words["group_column"] not in low or words["code_column"] not in low:
            continue
        if len(TANK_CODE.findall(text)) >= 3:
            found.append(index)
    return found


def _class_boundary(page, below: float) -> float:
    """Where the tank code column ends and the group columns begin.

    The tank code stands alone on the left of a wide table; the widest corridor
    in the left third of the page is the gutter after it.
    """
    corridors = _corridor(page, below)
    limit = page.rect.width / 3
    candidates = [(end - start, (start + end) / 2)
                  for start, end in corridors if end < limit]
    if not candidates:
        return limit
    return max(candidates)[1]


def rationalised_rows(doc, pages: list[int],
                      language: str) -> tuple[list[dict[str, Any]], list[str]]:
    """The group of substances each tank code is permitted to carry.

    The table sets a tank code once and then lists its group over many lines,
    leaving the class blank while it repeats — so a blank class means the class
    above, and a line without a tank code belongs to the code above. The
    sentence that ends a block names the codes whose groups this one inherits;
    it is kept as it is written, because the inheritance is what makes the table
    a hierarchy at all.
    """
    words = LANGUAGES[language]
    blocks: list[dict[str, Any]] = []
    failures: list[str] = []
    current: dict[str, Any] | None = None
    seen_class = ""

    for index in pages:
        page = doc[index]
        lines = _lines(page)
        header = next((y for y, items in lines
                       if words["code_column"] in flatten(
                           " ".join(w for _x, w in items)).lower()), 0.0)
        boundary = _class_boundary(page, header)
        for _y, items in lines:
            if _y <= header:
                continue
            text = flatten(" ".join(word for _x, word in items))
            inherit = words["inherit"].search(text)
            if inherit:
                if current is None:
                    failures.append(f"p{index + 1}: inheritance before any code")
                    continue
                current["inherits"] = [
                    code for code in TANK_CODE.findall(inherit.group(1)) or []
                ] or _codes_in(inherit.group(1))
                continue
            left = [word for x, word in items if x < boundary]
            right = [(x, word) for x, word in items if x >= boundary]
            code = next((word for word in left
                         if TANK_CODE.fullmatch(word.strip(","))), "")
            if code:
                current = {"tank_code": code.rstrip(")"), "groups": [],
                           "inherits": [], "page": index + 1}
                blocks.append(current)
                seen_class = ""
            if current is None:
                continue
            group, seen_class = _group(right, seen_class)
            if group:
                current["groups"].append(group)
            elif right and not code:
                failures.append(f"p{index + 1} {current['tank_code']}: {text[:70]!r}")
    return blocks, failures


def _codes_in(text: str) -> list[str]:
    return [match.group(0).rstrip(")") for match in TANK_CODE.finditer(text)]


def _group(items: list[tuple[float, str]],
           seen_class: str) -> tuple[dict[str, Any] | None, str]:
    """One line of the group columns: class, classification code, packing group.

    The class is printed once for a run of classification codes and left blank
    after that, so a blank one is the class above rather than a missing value.
    """
    tokens = [word.strip(",") for _x, word in items if word.strip(",")]
    if not tokens:
        return None, seen_class
    klass = seen_class
    if CLASS.fullmatch(tokens[0]):
        klass = tokens[0]
        tokens = tokens[1:]
    if not tokens:
        return None, klass
    code = tokens[0]
    if not CLASSIFICATION.fullmatch(code):
        return None, klass
    groups = [token for token in tokens[1:] if PACKING_GROUP.fullmatch(token)]
    if not klass:
        return None, klass
    return {"class": klass, "classification_code": code.rstrip(")"),
            "packing_groups": groups}, klass


# --- probing --------------------------------------------------------------


def probe(doc, language: str) -> int:
    gases = gas_pages(doc, language)
    rational = rationalised_pages(doc, language)
    print(f"pages: {doc.page_count}")
    print(f"gases (4.3.3.1.2): {[p + 1 for p in gases]}")
    print(f"rationalized (4.3.4.1.2): {[p + 1 for p in rational]}")
    for index in (gases + rational)[:6]:
        page = doc[index]
        print(f"--- page {index + 1} " + "-" * 40)
        print(f"corridors: {[(round(a), round(b)) for a, b in _corridor(page)][:12]}")
        for y, items in _lines(page)[:40]:
            cells = " | ".join(f"{round(x)}:{word}" for x, word in items)
            print(f"  {round(y, 1)} {cells[:150]}")
    return 0


# --- the two readings against each other ----------------------------------


def check(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """Compare two readings cell by cell, and keep every disagreement.

    A cell the two editions do not agree on is not a cell to choose between. It
    is stored with both values and counted as unsettled, so that what the
    application answers with is only ever what two books said the same.
    """
    report: dict[str, Any] = {"gases": [], "rationalised": [], "disputes": 0}

    a_gas = {row["tank_code"]: row for row in first["gases"]}
    b_gas = {row["tank_code"]: row for row in second["gases"]}
    for code in sorted(set(a_gas) | set(b_gas)):
        left, right = a_gas.get(code), b_gas.get(code)
        row: dict[str, Any] = {"tank_code": code, "readings": bool(left) + bool(right)}
        if left and right and left["also_permitted"] == right["also_permitted"]:
            row["also_permitted"] = left["also_permitted"]
        elif left and right:
            row["disputed"] = {"also_permitted": {
                first["language"]: left["also_permitted"],
                second["language"]: right["also_permitted"]}}
            report["disputes"] += 1
        else:
            source = left or right
            row["also_permitted"] = source["also_permitted"]
        report["gases"].append(row)

    a_rat = {row["tank_code"]: row for row in first["rationalised"]}
    b_rat = {row["tank_code"]: row for row in second["rationalised"]}
    for code in sorted(set(a_rat) | set(b_rat)):
        left, right = a_rat.get(code), b_rat.get(code)
        row = {"tank_code": code, "readings": bool(left) + bool(right)}
        for field in ("groups", "inherits"):
            if left and right and left[field] == right[field]:
                row[field] = left[field]
            elif left and right:
                row.setdefault("disputed", {})[field] = {
                    first["language"]: left[field], second["language"]: right[field]}
                report["disputes"] += 1
            else:
                row[field] = (left or right)[field]
        report["rationalised"].append(row)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read the ADR 4.3 tank hierarchies")
    parser.add_argument("--pdf", type=Path, help="the volume to read")
    parser.add_argument("--language", default="en", choices=sorted(LANGUAGES))
    parser.add_argument("--probe", action="store_true",
                        help="report the layout of the pages found and stop")
    parser.add_argument("--dump", action="store_true",
                        help="print every row to the log as well")
    parser.add_argument("--out", type=Path, help="write the reading here")
    parser.add_argument("--check", type=Path, nargs=2, metavar=("FIRST", "SECOND"),
                        help="compare two readings")
    parser.add_argument("--emit", type=Path, help="write the compared seed here")
    args = parser.parse_args()

    if args.check:
        first, second = (json.loads(path.read_text(encoding="utf-8"))
                         for path in args.check)
        report = check(first, second)
        print(json.dumps({k: v for k, v in report.items() if k == "disputes"}))
        if args.emit:
            args.emit.write_text(
                json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8")
        return 0

    if not args.pdf:
        parser.error("give --pdf or --check")

    import pymupdf

    with pymupdf.open(args.pdf) as doc:
        if args.probe:
            return probe(doc, args.language)
        gases, gas_failures = gas_rows(doc, gas_pages(doc, args.language))
        rational, rational_failures = rationalised_rows(
            doc, rationalised_pages(doc, args.language), args.language)

    reading = {"language": args.language, "gases": gases, "rationalised": rational}
    print(f"gases: {len(gases)} rows, {len(gas_failures)} failures")
    print(f"rationalized: {len(rational)} codes, {len(rational_failures)} failures")
    for line in (gas_failures + rational_failures)[:60]:
        print(f"  ! {line}")
    if args.dump:
        # The development container cannot reach the artifact store, so the log
        # is the way a reading gets home.
        print(f"READING {json.dumps(reading, ensure_ascii=False)}")
    if args.out:
        args.out.write_text(json.dumps(reading, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
