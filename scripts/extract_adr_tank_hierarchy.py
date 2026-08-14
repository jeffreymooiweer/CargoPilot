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
        "inherit_end": None,
        "and": re.compile(r"\band\b", re.IGNORECASE),
    },
    "nl": {
        "gases_heading": "hiërarchie van tanks",
        "gases_column": "andere tankcode",
        "code_column": "tankcode",
        "group_column": "groep van toegestane stoffen",
        "class_column": "klasse",
        "inherit": re.compile(
            r"groepen van de voor de tankcodes?(.*)", re.IGNORECASE | re.DOTALL),
        "inherit_end": re.compile(r"toegestane stoffen", re.IGNORECASE),
        "and": re.compile(r"\ben\b", re.IGNORECASE),
    },
    "de": {
        "gases_heading": "rangordnung der tanks",
        "gases_column": "andere tankcodierung",
        "code_column": "tankcodierung",
        "group_column": "gruppe der zugelassenen stoffe",
        "class_column": "klasse",
        "inherit": re.compile(
            r"gruppen der für die tankcodierungen?(.*)", re.IGNORECASE | re.DOTALL),
        "inherit_end": re.compile(r"zugelassenen stoffe", re.IGNORECASE),
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
    """The pages of the rationalized approach, header or no header.

    Requiring the table's headings on every page is what the first reader did,
    and the printed Dutch edition does not repeat them: page 846 fell out of
    the reading, the twenty-odd rows of L4BN with it, and the two rows that
    happened to sit on the next page were handed to the block above. So the
    heading is what finds the table, and the rows themselves are what say
    where it ends — the section runs on until a page stops looking like it.
    """
    words = LANGUAGES[language]
    start = None
    for index in range(doc.page_count):
        text = doc[index].get_text()
        if _is_contents(text):
            continue
        low = text.lower()
        if (words["group_column"] in low and words["code_column"] in low
                and len(TANK_CODE.findall(text)) >= 3):
            start = index
            break
    if start is None:
        return []

    found = [start]
    for index in range(start + 1, doc.page_count):
        if _rows_of_the_table(doc[index]) < 5:
            break
        found.append(index)
    return found


def _rows_of_the_table(page) -> int:
    """How many lines of this page read as rows of the rationalized approach."""
    rows = 0
    for _y, items in _lines(page):
        tokens, _markers = _strip_markers(
            [word.strip(",").strip() for _x, word in items])
        if not tokens:
            continue
        if TANK_CODE.fullmatch(tokens[0]):
            tokens = tokens[1:]
        if tokens and CLASS.fullmatch(tokens[0]):
            tokens = tokens[1:]
        if (tokens and CLASSIFICATION.fullmatch(tokens[0])
                and all(PACKING_GROUP.fullmatch(token) for token in tokens[1:])):
            rows += 1
    return rows


def rationalised_rows(doc, pages: list[int],
                      language: str) -> tuple[list[dict[str, Any]], list[str]]:
    """The group of substances each tank code is permitted to carry.

    The table sets a tank code once and then lists its group over many lines,
    leaving the class blank while it repeats — so a blank class means the class
    above, and a line without a tank code belongs to the code above. The
    sentence that ends a block names the codes whose groups this one inherits;
    that inheritance is what makes the table a hierarchy at all, so it is read
    rather than skipped, over as many lines as the sentence takes.

    Where the columns are is not measured, because it does not have to be. The
    four columns hold four shapes that cannot be mistaken for each other — a
    tank code begins with L or S and has a fixed form, a class is a bare digit
    with at most one decimal, a classification code is capitals and digits, a
    packing group is one to three I's — and they are printed in that order. So
    a line is read by what its tokens are, which also means a running head, a
    page number or a footnote is not a line of the table at all: it carries a
    token that is none of those four things.
    """
    words = LANGUAGES[language]
    blocks: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    failures: list[str] = []
    current: dict[str, Any] | None = None
    seen_class = ""
    inheriting = False

    def block(code: str, page: int) -> dict[str, Any]:
        # A block that runs over a page break has its tank code printed again
        # at the head of the continuation, and the same code is never two
        # blocks — so the second sight of it continues the first.
        if code not in blocks:
            blocks[code] = {"tank_code": code, "groups": [], "inherits": [],
                            "sentence": "", "pages": []}
            order.append(code)
        if page not in blocks[code]["pages"]:
            blocks[code]["pages"].append(page)
        return blocks[code]

    for index in pages:
        for _y, items in _lines(doc[index]):
            text = flatten(" ".join(word for _x, word in items))
            tokens, markers = _strip_markers(
                [word.strip(",").strip() for _x, word in items])

            # The inheritance is a sentence, and a sentence is not a line. The
            # English edition sets it on one and wraps the tail — "… L10BH and"
            # / "L10CH" — while the Dutch wraps it in the middle and closes it
            # two lines later with "toegestane stoffen". Read as lines it comes
            # out as a new block with no group, which is how L4BN, L10CH and
            # SGAN went missing from the Dutch reading altogether.
            if inheriting:
                # What the sentence actually said is kept beside what was made
                # of it: when two readings disagree about an inheritance, the
                # sentence is the evidence, and without it the next correction
                # is a guess about a line nobody has seen.
                if current is not None:
                    current["sentence"] = f"{current.get('sentence', '')} {text}".strip()
                # A sentence that never meets its closing words would run to
                # the end of the table, swallowing the blocks after it: the
                # Dutch reading had L4BN, L10CH, L15CH and L21DH inside
                # L10DH's inheritance and missing from the table. So the tail
                # of a sentence is only ever a line of tank codes and the
                # edition's own joining words. Anything else ends it, and is
                # then read as the line it is.
                closes = _closing(text, words)
                tail = _codes_in(text)
                if closes or _only_codes(text, tokens, words):
                    if current is not None:
                        for code in tail:
                            if code not in current["inherits"]:
                                current["inherits"].append(code)
                    inheriting = not closes and _sentence_runs_on(text, words)
                    continue
                inheriting = False

            inherit = words["inherit"].search(text)
            if inherit:
                # Which block the sentence belongs to is a matter of where the
                # edition puts it. The English volume sets it at the end of a
                # block's cell, so it belongs to the block being read. The
                # printed Dutch edition sets it at the *start*, on the same
                # line as the tank code it belongs to — and a reader that took
                # that line for the block above lost the block itself and gave
                # its rows to its predecessor. L4BN and L10CH went missing that
                # way, and L1,5BN came back inheriting from itself.
                if tokens and TANK_CODE.fullmatch(tokens[0]) and text.startswith(tokens[0]):
                    current = block(tokens[0], index + 1)
                    seen_class = ""
                if current is None:
                    failures.append(f"p{index + 1}: inheritance before any code")
                    continue
                current["sentence"] = text
                for code in _codes_in(inherit.group(1)):
                    if code not in current["inherits"]:
                        current["inherits"].append(code)
                inheriting = _sentence_runs_on(text, words)
                continue

            # A packing group on a line of its own belongs to the row above:
            # both editions wrap "II, III" that way, and read as a row of its
            # own it becomes a group whose classification code is "III" — the
            # one shape a packing group and a classification code share.
            if (tokens and current is not None and current["groups"]
                    and all(PACKING_GROUP.fullmatch(token) for token in tokens)):
                current["groups"][-1]["packing_groups"].extend(tokens)
                continue

            codes = [token for token in tokens if TANK_CODE.fullmatch(token)]
            if codes and TANK_CODE.fullmatch(tokens[0]):
                current = block(tokens[0], index + 1)
                seen_class = ""
                tokens = tokens[1:]

            if current is None or not tokens:
                continue
            group, seen_class = _group(tokens, seen_class)
            if group:
                if markers and "footnote" not in group:
                    group["footnote"] = "".join(markers)
                current["groups"].append(group)
    return [_as_triples(blocks[code]) for code in order], failures


def _as_triples(block: dict[str, Any]) -> dict[str, Any]:
    """One row per class, classification code and packing group.

    The editions do not agree on how to *set* a row and there is no reason they
    should: the English volume prints "F1 II" and "F1 III" on two lines where
    the Dutch prints "F1 II, III" on one. That is typesetting, not content, and
    comparing the lines would report a disagreement where the two books say
    exactly the same thing. A permission is a class, a classification code and
    a packing group; where the regulation assigns no packing group — class 6.2
    is the case — the permission has none, and that is a value too.
    """
    permitted: list[dict[str, Any]] = []
    for group in block["groups"]:
        for packing_group in group["packing_groups"] or [None]:
            row = {"class": group["class"],
                   "classification_code": group["classification_code"],
                   "packing_group": packing_group}
            if group.get("footnote"):
                row["footnote"] = group["footnote"]
            if row not in permitted:
                permitted.append(row)
    return {"tank_code": block["tank_code"], "permitted": permitted,
            "inherits": block["inherits"], "sentence": block["sentence"],
            "pages": block["pages"]}


#: A footnote marker as the table sets it against a cell: a single lower-case
#: letter, sometimes with the bracket it is printed with. Left in the line it
#: would fail every column's shape and take the whole row down with it — which
#: is what happened to class 6.1 T1 under L10CH, and to the class cell with it,
#: so that six rows below it were read as class 3.
MARKER = re.compile(r"[a-z]\)?")


def _strip_markers(tokens: list[str]) -> tuple[list[str], list[str]]:
    kept, markers = [], []
    for token in tokens:
        if not token:
            continue
        if MARKER.fullmatch(token):
            markers.append(token.rstrip(")"))
        else:
            kept.append(token)
    return kept, markers


def _closing(text: str, words: dict[str, Any]) -> bool:
    """Does this line carry the words the edition ends the sentence with?"""
    end = words.get("inherit_end")
    return bool(end and end.search(text))


def _only_codes(text: str, tokens: list[str], words: dict[str, Any]) -> bool:
    """Is this line nothing but tank codes and the words that join them?"""
    if not tokens:
        return False
    joined = words["and"]
    return all(TANK_CODE.fullmatch(token) or joined.fullmatch(token)
               for token in tokens)


def _sentence_runs_on(text: str, words: dict[str, Any]) -> bool:
    """Is the inheritance sentence still open after this line?

    Where the edition ends the sentence with words of its own — the Dutch
    "toegestane stoffen", the German "zugelassenen Stoffe" — those words close
    it, and nothing else does. The English sentence ends where its list does,
    so it is the comma or the conjunction at the line's end that says it runs
    on.
    """
    tail = text.rstrip()
    closing = words.get("inherit_end")
    if closing is not None:
        return not closing.search(tail)
    return tail.endswith(",") or bool(words["and"].search(tail[-6:]))


def _codes_in(text: str) -> list[str]:
    return [match.group(0).rstrip(")") for match in TANK_CODE.finditer(text)]


def _group(tokens: list[str],
           seen_class: str) -> tuple[dict[str, Any] | None, str]:
    """One line of the group columns: class, classification code, packing group.

    The class is printed once for a run of classification codes and left blank
    after that, so a blank one is the class above rather than a missing value.
    A line that carries anything else is not a line of the table, and is left
    alone rather than half-read: that is what keeps the running head, the page
    number and the footnote out of the group.
    """
    if not tokens:
        return None, seen_class
    klass = seen_class
    if CLASS.fullmatch(tokens[0]):
        klass = tokens[0]
        tokens = tokens[1:]
    if not tokens or not CLASSIFICATION.fullmatch(tokens[0]):
        return None, klass
    code = tokens[0]
    if not all(PACKING_GROUP.fullmatch(token) for token in tokens[1:]):
        return None, klass
    if not klass:
        return None, klass
    # A classification code is capitals and digits; a lower-case letter against
    # it is the table's footnote marker and not part of the code. Keeping them
    # apart matters because the marker is what carries the exception — "except
    # hydrofluoric acid" hangs off one of these letters.
    group: dict[str, Any] = {"class": klass, "classification_code": code.rstrip(
        "abcdefghijklmnopqrstuvwxyz"), "packing_groups": tokens[1:]}
    marker = code[len(group["classification_code"]):]
    if marker:
        group["footnote"] = marker
    return group, klass


# --- probing --------------------------------------------------------------


def words(doc, language: str) -> int:
    """Print the geometry of the table pages, once, as one JSON line.

    The volumes live on a runner and the development container cannot reach
    them, so every correction to the reader would otherwise cost a CI run to
    find out what it did. The words and their positions are all a reader needs;
    with them saved outside the repository the parser can be fixed against the
    real page in the container, and the runner is asked again only to confirm.
    """
    pages = {}
    for index in gas_pages(doc, language) + rationalised_pages(doc, language):
        pages[index + 1] = [[round(y, 1), [[round(x, 1), word] for x, word in items]]
                            for y, items in _lines(doc[index])]
    print(f"WORDS {json.dumps({'language': language, 'pages': pages}, ensure_ascii=False)}")
    return 0


def probe_page(doc, number: int) -> int:
    """One page, line by line, with the x of every word.

    Guessing what a page looks like from what a reader made of it is how three
    runs get spent on a layout nobody has looked at. This is the looking.
    """
    page = doc[number - 1]
    print(f"--- page {number} of {doc.page_count} " + "-" * 30)
    for y, items in _lines(page):
        cells = " | ".join(f"{round(x)}:{word}" for x, word in items)
        print(f"{round(y, 1)} {cells[:170]}")
    return 0


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

    a_rat = {_canonical(row["tank_code"]): row for row in first["rationalised"]}
    b_rat = {_canonical(row["tank_code"]): row for row in second["rationalised"]}
    for code in sorted(set(a_rat) | set(b_rat)):
        left, right = a_rat.get(code), b_rat.get(code)
        row = {"tank_code": code, "readings": bool(left) + bool(right)}
        for field in ("permitted", "inherits"):
            here = _comparable(left, field) if left else None
            there = _comparable(right, field) if right else None
            if left and right and here == there:
                row[field] = left[field]
            elif left and right:
                row.setdefault("disputed", {})[field] = {
                    first["language"]: left[field], second["language"]: right[field]}
                row.setdefault("only_in", {})[field] = {
                    first["language"]: sorted(set(here) - set(there)),
                    second["language"]: sorted(set(there) - set(here))}
                if field == "inherits":
                    row["sentences"] = {first["language"]: left.get("sentence", ""),
                                        second["language"]: right.get("sentence", "")}
                report["disputes"] += 1
            else:
                row[field] = (left or right)[field]
        report["rationalised"].append(row)
    return report


def _canonical(code: str) -> str:
    """One spelling of a tank code, so two editions can be compared at all.

    The English volume prints L1.5BN and the Dutch L1,5BN. That is a decimal
    separator, not a difference about the tank, and treating it as one would
    leave both editions' rows unmatched and every cell in them unsettled.
    """
    return code.replace(",", ".")


def _comparable(block: dict[str, Any], field: str) -> list[str]:
    """A field flattened to strings, so the comparison is about content."""
    if field == "inherits":
        return [_canonical(code) for code in block[field]]
    return [f"{row['class']}/{row['classification_code']}/{row['packing_group'] or '-'}"
            for row in block[field]]


def report_differences(report: dict[str, Any], first: str, second: str) -> None:
    """Say where the two readings differ, and nothing else.

    Between corrections this is the only thing worth printing: the readings
    themselves are ten thousand characters each, and what a run has to answer
    is which cells two books do not yet say the same thing about.
    """
    for row in report["gases"]:
        if row.get("disputed"):
            sides = row["disputed"]["also_permitted"]
            print(f"  gases {row['tank_code']}: {first}={sides[first]} "
                  f"{second}={sides[second]}")
        elif row["readings"] < 2:
            print(f"  gases {row['tank_code']}: only one reading")
    for row in report["rationalised"]:
        if row["readings"] < 2:
            print(f"  {row['tank_code']}: only one reading")
            continue
        for field, sides in (row.get("only_in") or {}).items():
            print(f"  {row['tank_code']} {field}: "
                  f"only {first} {sides[first]} / only {second} {sides[second]}")
            if field == "inherits":
                for language, sentence in (row.get("sentences") or {}).items():
                    print(f"      {language}: {sentence[:150]!r}")
    print(f"disputes: {report['disputes']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read the ADR 4.3 tank hierarchies")
    parser.add_argument("--pdf", type=Path, help="the volume to read")
    parser.add_argument("--language", default="en", choices=sorted(LANGUAGES))
    parser.add_argument("--probe", action="store_true",
                        help="report the layout of the pages found and stop")
    parser.add_argument("--words", action="store_true",
                        help="print the geometry of the pages found and stop")
    parser.add_argument("--probe-page", type=int, default=0,
                        help="print one page line by line, with the x of every word")
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
        report_differences(report, first["language"], second["language"])
        if args.emit:
            args.emit.write_text(
                json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8")
        return 0

    if not args.pdf:
        parser.error("give --pdf or --check")

    import pymupdf

    with pymupdf.open(args.pdf) as doc:
        if args.probe_page:
            return probe_page(doc, args.probe_page)
        if args.words:
            return words(doc, args.language)
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
