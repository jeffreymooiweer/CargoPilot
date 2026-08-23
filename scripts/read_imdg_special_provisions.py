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

The one thing worth distrusting here is the split. Chapter 3.3 sets the
provision number in a narrow left column and its text beside it, which the text
layer returns as a bare number on its own line followed by the prose. Bare
numbers appear inside provisions too — quantities, cross-references, page
furniture — so a naive split invents provisions and swallows real ones. Two
invariants keep it honest: a number only starts a provision if column 6 uses it
or the Code's own index lists it, and the numbers must ascend. A break in the
ascent is reported rather than smoothed over, because a parser that quietly
reorders a regulation is worse than one that stops.
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


def _chapter_text(document, known: set[str]) -> tuple[str, int, int]:
    """The text of chapter 3.3, with the printed page numbers it spans.

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
    body = "\n".join(document[n].get_text() for n in range(first, last + 1))
    return body, first + 1, last + 1


def _split(body: str, known: set[str]) -> tuple[dict[str, str], list[str]]:
    """Chapter 3.3 as {number: text}, plus whatever looked wrong.

    A line that is nothing but a number opens a provision, but only if column 6
    cites that number and it is larger than the one before it. Both conditions
    are needed: the first keeps quantities and cross-references out, the second
    keeps a stray page number from resetting the sequence.
    """
    provisions: dict[str, str] = {}
    complaints: list[str] = []
    current: str | None = None
    lines: list[str] = []
    highest = 0
    for line in body.splitlines():
        token = line.strip()
        if token.isdigit() and token in known:
            value = int(token)
            if value > highest:
                if current is not None:
                    provisions[current] = " ".join(" ".join(lines).split())
                current, lines, highest = token, [], value
                continue
            complaints.append(
                f"{token} appears after {highest} and was left inside the text "
                f"of provision {current}")
        if current is not None:
            lines.append(token)
    if current is not None:
        provisions[current] = " ".join(" ".join(lines).split())
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
    body, first, last = _chapter_text(document, known)
    provisions, complaints = _split(body, known)

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
