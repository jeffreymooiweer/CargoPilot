#!/usr/bin/env python3
"""Find which special provisions of IMDG chapter 3.3 speak about labelling.

Column 6 of the Dangerous Goods List is the one thing the sea answer of
chapter 5.2 has always refused to claim it had read. IMDG 5.2.2.1.2 lets a
special provision add a subsidiary label where column 4 shows none and remove
one where it does, and 5.2.2.1.2.1 lets one drop the labelling altogether for a
substance of a low degree of danger. Two hundred and sixty-two distinct
provision numbers appear in column 6 across the list. Reading all of them by
hand to find the handful that touch labels is the kind of task that gets done
once, badly, and is never checked again.

So this reads them. It splits chapter 3.3 into numbered provisions, matches
each number against the ones column 6 actually uses, and prints the text of
every provision whose wording mentions a label. What a human then does with
that is decide, per provision, what the fact is — "adds model 1", "no label at
all", "marking instead of labelling" — and put that in
``seed/dg/package_marking.json`` through a reviewed change. The regulation's
text is not ours to redistribute; the facts read out of it are.

Runs on a runner, where the Code can be reached::

    python scripts/read_imdg_special_provisions.py
    python scripts/read_imdg_special_provisions.py --all --number 29

It commits nothing.

The one thing worth distrusting here is the split, and the first two attempts
at it were both wrong in ways that still produced output.

Chapter 3.3 sets the provision number in a narrow column down the left edge and
its text beside it. Read as a stream of lines, that comes back as a *block* of
numbers followed by a block of prose — so provision 199 swallowed forty of its
neighbours and the run reported two hundred and ten provisions as though it had
them. Reading order cannot fix this, because the same numbers appear inside the
prose all over the chapter and nothing in the sequence distinguishes them.

So the number is found by *where it stands*. The column's x is measured from the
page — the most crowded position among words that are nothing but a number
column 6 cites — and printed, because a calibration nobody sees is a constant in
disguise. Ascending order is then no longer a rule but a report: if the split is
right the sequence rises by itself, so a break in it is news about the parser.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

try:
    import pymupdf
except ImportError:  # pragma: no cover - the runner installs it
    print("PyMuPDF is required: pip install pymupdf", file=sys.stderr)
    raise SystemExit(2)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from read_land_regulations import SOURCES, fetch  # noqa: E402

SEED = pathlib.Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg"

#: The heading that opens the chapter, and the one that closes it. Chapter 3.3
#: is a single run of numbered provisions between the two.
#
#: Neither is unique. The heading appears in the table of contents hundreds of
#: pages earlier, and the first run of this script found *that* — coming back
#: with six provisions cut out of the front matter and reporting it as a
#: success, which is the failure mode a reading tool must not have. So the
#: opening heading is not trusted on sight: the page that carries it only counts
#: as the start of the chapter if the pages after it actually look like a run of
#: numbered provisions.
START = "Special provisions applicable to certain substances, materials or articles"
END = "Chapter 3.4"

#: How many bare provision numbers have to appear in the pages after a candidate
#: heading before it is believed. A contents line is followed by more contents;
#: the chapter is followed by provisions.
PROOF = 5

#: What counts as a provision that touches labelling. Deliberately wider than
#: "label": a provision that says a package is *marked* instead of labelled
#: changes the answer just as much as one that names a model, and 5.2.2.1.2 is
#: about both adding and removing. Anything this matches gets printed in full
#: and judged by a human; anything it misses is a provision nobody reads, which
#: is why the pattern errs towards noise.
LABELLING = re.compile(
    r"\blabel(?:s|led|ling)?\b|\bplacard|\bmark(?:ed|ing)?\b|\bmodel No\.|"
    r"\bsubsidiary (?:hazard|risk)|\bexempt(?:ed)? from",
    re.IGNORECASE,
)


def _column_six_numbers() -> set[str]:
    """Every provision number column 6 actually uses, from the read list.

    A provision the list never cites cannot change any package in this
    application, and letting it start a section only gives the split more ways
    to go wrong.
    """
    data = json.loads((SEED / "imdg_dgl.json").read_text(encoding="utf-8"))
    found: set[str] = set()
    for entry in data.get("entries", []):
        found.update(re.findall(r"\d+", str(entry.get("special_provisions") or "")))
    return found


def _looks_like_provisions(document, start: int, known: set[str]) -> int:
    """How many bare provision numbers stand in the three pages after ``start``."""
    found = 0
    for number in range(start, min(start + 3, document.page_count)):
        for line in document[number].get_text().splitlines():
            token = line.strip()
            if token.isdigit() and token in known:
                found += 1
    return found


def _chapter_pages(document, known: set[str]) -> tuple[int, int]:
    """The printed pages chapter 3.3 spans.

    The heading is checked against what follows it rather than taken at its
    word, because the table of contents carries the same sentence and sits
    hundreds of pages earlier.
    """
    candidates = [n for n in range(document.page_count)
                  if START in " ".join(document[n].get_text().split())]
    if not candidates:
        raise SystemExit("chapter 3.3 was not found in this document")
    scored = [(n, _looks_like_provisions(document, n, known)) for n in candidates]
    first, proof = max(scored, key=lambda item: item[1])
    if proof < PROOF:
        raise SystemExit(
            "no page carrying the chapter 3.3 heading is followed by provisions "
            f"(best was printed page {first + 1} with {proof} of them); "
            "the chapter was not read rather than read wrongly")
    rejected = [n + 1 for n, score in scored if n != first]
    if rejected:
        print(f"heading also appears on printed page(s) "
              f"{', '.join(str(n) for n in rejected)}, not followed by provisions")

    last = None
    for number in range(first + 1, document.page_count):
        if END in " ".join(document[number].get_text().split()):
            last = number - 1
            break
    last = last if last is not None else min(first + 60, document.page_count - 1)
    return first + 1, last + 1


def _words(document, first: int, last: int) -> list[tuple[int, float, float, str]]:
    """Every word of the chapter as (page, y, x, text), in reading order.

    Sorted explicitly rather than trusting the order the text layer hands
    back. That order is by *block*, and chapter 3.3 sets its provision numbers
    in a block of their own down the left edge — so reading it as it comes
    yields a page of numbers followed by a page of prose, which is exactly the
    shape that made a single provision swallow forty of its neighbours.
    """
    items: list[tuple[int, float, float, str]] = []
    for page in range(first - 1, last):
        for x0, y0, _x1, _y1, word, *_rest in document[page].get_text("words"):
            items.append((page, round(y0, 1), round(x0, 1), word))
    items.sort(key=lambda item: (item[0], item[1], item[2]))
    return items


def _number_column(items, known: set[str]) -> float:
    """Where the provision numbers stand, measured rather than assumed.

    Every provision number sits at the same left edge; the numbers that appear
    inside prose are scattered across the width. So the most crowded x, among
    words that are nothing but a number column 6 cites, is the column — and it
    is reported, because a calibration nobody sees is a constant in disguise.
    """
    tally: dict[int, int] = {}
    for _page, _y, x, word in items:
        if word.isdigit() and word in known:
            tally[round(x)] = tally.get(round(x), 0) + 1
    if not tally:
        raise SystemExit("no provision numbers found in the chapter text")
    ranked = sorted(tally.items(), key=lambda item: -item[1])
    print("where words that are nothing but a cited number stand, by x:")
    for x, crowd in ranked[:12]:
        print(f"    x={x:>5}  {crowd:>4}")
    if len(ranked) > 12:
        print(f"    … and {len(ranked) - 12} further positions, "
              f"{sum(c for _x, c in ranked[12:])} words in all")
    column, crowd = ranked[0]
    print(f"taking x={column} as the number column ({crowd} of them); "
          f"anything further right is text")
    return float(column)


#: How far a word may sit from the measured column and still count as a
#: provision number. A point either way covers rounding in the text layer
#: without reaching the prose, which starts tens of points to the right.
COLUMN_TOLERANCE = 2.0


def _split(items, known: set[str], column: float) -> tuple[dict[str, str], list[str]]:
    """Chapter 3.3 as {number: text}, plus whatever looked wrong.

    A word opens a provision when it is nothing but a number column 6 cites
    *and* it stands in the number column. Position is what makes this reliable:
    the same numbers appear inside prose all over the chapter, and no amount of
    reading order tells them apart.

    The ascending order of the numbers is no longer used to decide anything —
    only to report. If the split is right the sequence rises on its own, so a
    break in it is news about the parser rather than a rule for it.
    """
    provisions: dict[str, str] = {}
    complaints: list[str] = []
    current: str | None = None
    words: list[str] = []
    highest = 0
    for _page, _y, x, word in items:
        if word.isdigit() and word in known and abs(x - column) <= COLUMN_TOLERANCE:
            if current is not None:
                provisions[current] = " ".join(" ".join(words).split())
            if int(word) <= highest:
                complaints.append(
                    f"{word} stands in the number column but does not follow "
                    f"{highest}")
            current, words, highest = word, [], max(highest, int(word))
            continue
        if current is not None and x > column + COLUMN_TOLERANCE:
            words.append(word)
    if current is not None:
        provisions[current] = " ".join(" ".join(words).split())
    return provisions, complaints


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", default="imdg_42_24")
    parser.add_argument("--all", action="store_true",
                        help="print every provision, not only the ones about labels")
    parser.add_argument("--number", action="append", default=[],
                        help="print this provision in full, whatever it says")
    parser.add_argument("--chars", type=int, default=900,
                        help="how much of each provision to print")
    args = parser.parse_args()

    if args.doc not in SOURCES:
        print(f"{args.doc}: not a known document id", file=sys.stderr)
        return 1

    known = _column_six_numbers()
    document = pymupdf.open(fetch(args.doc))
    first, last = _chapter_pages(document, known)
    items = _words(document, first, last)
    page = document[first - 1].rect
    print(f"chapter pages measure {page.width:.0f} x {page.height:.0f} points; "
          f"words run from x={min(i[2] for i in items):.0f} to "
          f"x={max(i[2] for i in items):.0f}")
    provisions, complaints = _split(items, known, _number_column(items, known))

    print(SOURCES[args.doc]["title"])
    print(f"chapter 3.3 on printed pages {first}-{last}")
    print(f"column 6 of the Dangerous Goods List cites {len(known)} distinct "
          f"provision numbers; {len(provisions)} of them were found here")
    missing = sorted(known - set(provisions), key=int)
    if missing:
        print(f"NOT FOUND in chapter 3.3: {' '.join(missing)}")
    for complaint in complaints:
        print(f"  ordering: {complaint}")
    print("=" * 78)

    wanted = set(args.number)
    about_labels = [n for n in sorted(provisions, key=int)
                    if LABELLING.search(provisions[n])]
    shown = sorted(
        set(about_labels) | wanted if not args.all else set(provisions),
        key=int)
    for number in shown:
        text = provisions.get(number, "(not found)")
        flag = "" if number in about_labels else "   [not matched — asked for]"
        print(f"\n[{number}]{flag}")
        print(f"  {text[:args.chars]}"
              + ("…" if len(text) > args.chars else ""))

    print("\n" + "=" * 78)
    print(f"{len(about_labels)} of {len(provisions)} provisions mention a label, "
          f"a mark or an exemption:")
    print("  " + " ".join(about_labels))
    # Everything a reader needs to judge the read, repeated at the end. A run
    # log reaches this container tail-first, and the provisions themselves are
    # long enough to push the header — including the list of numbers that were
    # never found — out of the only view there is.
    coverage = len(provisions) / len(known) if known else 0.0
    print("\n" + "=" * 78)
    print(f"chapter 3.3 on printed pages {first}-{last}")
    print(f"column 6 cites {len(known)} numbers; {len(provisions)} were found "
          f"here ({coverage:.0%})")
    if missing:
        print(f"NOT FOUND: {' '.join(missing)}")
    for complaint in complaints:
        print(f"  ordering: {complaint}")

    print("\nDecide per provision what the fact is, and put that in")
    print("backend/seed/dg/package_marking.json through a reviewed change.")
    print("Nothing is committed here, and no regulatory text enters the repo.")

    # A partial read is the dangerous outcome, not an empty one: it looks like
    # an answer. Every number column 6 cites should be defined in chapter 3.3,
    # and one that is missing has not vanished — its text has been swallowed by
    # the provision before it, which is how a label rule ends up filed under the
    # wrong number. So anything short of complete fails the run.
    if missing:
        print(f"\n{len(missing)} cited provisions were not found. Their text is "
              "not missing, it is attributed to whichever provision precedes "
              "them — which is worse.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
