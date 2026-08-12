"""Read the proper shipping names out of ADR 2025 in whatever language it is in.

ADR 2025 is published free of charge by UNECE in **English and French**, and
`scripts/read_land_regulations.py` already knows how to fetch it. Column (2) of
table A is therefore obtainable in three of the four languages this application
speaks, from the edition it computes with, and the two errata the manifest has
been carrying since v1.56.0 exist only because nobody had gone and got them:

- the English and German names still come from a **2023** export, because the
  Dutch edition read in v1.56.0 has no such column;
- fourteen UN numbers have no usable English name at all in that export, and
  UN 1139 has the truncated "Coating solution (".

This closes the first for English and adds French, which the application has
never had. **German it cannot close.** There is no free official German ADR,
and the alternative — machine-translating the English name — would be worse than
what is already there: `un_numbers.json` carries the *official* German name from
the 2023 edition, and an edition-old official name beats a fresh invented one.
A proper shipping name is not a phrase to be rendered; on a Shipper's
Declaration it is the identity of the goods.

## What this reuses

Everything. `extract_adr_table_a.py` had to find its own column boundaries on a
page that draws none, and none of that is language-specific: the same "(1) (2)
(3a) …" band stands above the table in every edition. So this imports that
reader and asks it for two columns instead of twenty-three.

What *is* different is the document. The Dutch table A came as a standalone
extract, 294 pages of nothing else. Volume I is the whole of parts 1 to 3, so
most of its pages have no table on them at all — a page without the marker band
is skipped rather than reported, or the log would be five hundred lines of
"no column numbers found" with the real problems buried in it.

Usage::

    python scripts/extract_adr_names_multilingual.py --pdf ADR_2025_Vol_I_E.pdf \\
        --language en --out backend/seed/dg/adr_names_en.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from read_land_regulations import SOURCES, fetch  # noqa: E402
from extract_adr_table_a import (  # noqa: E402
    COLS,
    UN_START,
    learn_left_ratios,
    learn_marker_ratios,
    read_page,
    un_and_name,
)

SEED = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg"

#: What the reading is compared against: the Dutch table already in the
#: repository. Two editions of one table in two languages hold the same UN
#: numbers, and a reading that does not is a reading that went wrong.
REFERENCE = SEED / "adr_table_a.json"


def read(path: Path) -> tuple[dict[str, list[str]], list[str], dict[str, int]]:
    """The names per UN number, in the order table A gives them."""
    import fitz

    names: dict[str, list[str]] = defaultdict(list)
    problems: list[str] = []
    counts = {"pages": 0, "table_pages": 0, "rows": 0}

    with fitz.open(path) as document:
        counts["pages"] = document.page_count
        ratios = learn_marker_ratios(document)
        if not ratios:
            return {}, ["no page in this document carries the column numbers of "
                        "table A — is this the volume that holds chapter 3.2?"], counts
        left_ratios = learn_left_ratios(document, ratios)

        carried: str | None = None
        for index in range(document.page_count):
            rows, page_problems = read_page(document[index], index + 1,
                                            ratios, left_ratios)
            # A page of running text is not a problem, it is most of the book.
            # Only a page that *has* the band and could not be laid out is.
            if not rows and page_problems and "no column numbers" in page_problems[0]:
                continue
            problems.extend(page_problems)
            if not rows:
                continue
            counts["table_pages"] += 1
            for row in rows:
                number, name = un_and_name(row)
                if number is None:
                    # A name running over the page break belongs to the row that
                    # began at the foot of the page before.
                    if carried and name:
                        names[carried][-1] = f"{names[carried][-1]} {name}".strip()
                    continue
                carried = number
                counts["rows"] += 1
                if name and name not in names[number]:
                    names[number].append(name)
    return dict(names), problems, counts


def probe(path: Path, samples: int = 6) -> None:
    """Report what the table pages of this edition actually look like.

    The Dutch table A came as a standalone extract with all twenty-three column
    numbers in one band above every page. The UNECE volume answered with none at
    all, which is a difference in the document and not a fault in the reading —
    the printed ADR lays table A across a two-page spread, so a page carries
    half the columns and the band never reaches the fifteen the reader looks
    for. Guessing which half would be guessing; this prints it.
    """
    import fitz
    import re as _re

    token = _re.compile(r"^\((\d{1,2}[ab]?)\)$")
    with fitz.open(path) as document:
        print(f"{document.page_count} pages")
        found = []
        for index in range(document.page_count):
            words = document[index].get_text("words")
            marks: dict[float, list[tuple[float, str]]] = defaultdict(list)
            for x0, y0, _x1, _y1, word, *_rest in words:
                hit = token.match(word.strip())
                if hit:
                    marks[round(y0, 0)].append((round(x0, 1), hit.group(1)))
            best = max((row for row in marks.values()), key=len, default=[])
            if len(best) >= 4:
                found.append((index + 1, sorted(best)))
        print(f"pages with a band of four or more column numbers: {len(found)}")
        for number, band in found[:samples]:
            print(f"  p{number}: {len(band)} -> "
                  + " ".join(f"({name})@{x:.0f}" for x, name in band))
        if not found:
            # Nothing recognisable at all: say what the pages do hold, or the
            # next run is another guess.
            print("  none. First lines of three pages in the middle:")
            for index in (document.page_count // 3,
                          document.page_count // 2,
                          2 * document.page_count // 3):
                head = " | ".join(
                    line.strip() for line in
                    document[index].get_text().splitlines()[:6] if line.strip())
                print(f"    p{index + 1}: {head[:220]}")


def against_the_dutch(names: dict[str, list[str]]) -> dict[str, Any]:
    """The self-check: the same table in another language holds the same rows.

    Not a comparison of the names — they are in different languages and are
    supposed to differ. What is compared is the *set of UN numbers*, which is a
    property of the table and not of the language. A column boundary that has
    slipped loses entries, and losing entries is exactly what this catches.
    """
    try:
        payload = json.loads(REFERENCE.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - seed missing
        return {"agreement": None}
    known = {row["un"] for row in payload.get("entries", [])}
    read_uns = set(names)
    shared = known & read_uns
    return {
        "same": len(shared),
        "only_in_this_language": sorted(read_uns - known)[:20],
        "only_in_the_dutch_table": sorted(known - read_uns)[:20],
        "agreement": round(len(shared) / len(known), 4) if known else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path,
                        help="An ADR volume already on disk that holds table A")
    parser.add_argument("--source", choices=sorted(SOURCES),
                        help="Fetch this text instead. UNECE answers a bare "
                             "request from a runner with 403, and the regulation "
                             "reader already knows the way round that — browser "
                             "headers first, the web archive after. Hand-rolling "
                             "the download here got a 403 twice and taught "
                             "nothing that file did not already know.")
    parser.add_argument("--language", default="en", choices=["en", "fr"],
                        help="Which language this volume is in")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--edition", default="ADR 2025")
    parser.add_argument("--probe", action="store_true",
                        help="Report the layout of this edition and stop")
    parser.add_argument("--dry-run", action="store_true",
                        help="Read and check, but do not write anything")
    parser.add_argument("--min-agreement", type=float, default=0.98,
                        help="Below this agreement nothing is written")
    args = parser.parse_args(argv)

    path = args.pdf
    if path is None:
        if not args.source:
            parser.error("give either --pdf or --source")
        path = fetch(args.source)
        print(f"read {SOURCES[args.source]['title']} "
              f"({SOURCES[args.source].get('resolved_via', 'direct')})")
    if args.probe:
        probe(path)
        return 0
    names, problems, counts = read(path)
    print(f"{counts['pages']} pages, {counts['table_pages']} of them table A, "
          f"{counts['rows']} rows, {len(names)} UN numbers")
    for problem in problems[:10]:
        print("  ", problem)
    if not names:
        print("No names read.")
        return 1

    check = against_the_dutch(names)
    print(f"\n--- against the Dutch table A already in the repository ---")
    print(f"  {check.get('same')} UN numbers in both, "
          f"agreement {check.get('agreement')}")
    if check.get("only_in_the_dutch_table"):
        print(f"  missing here: {check['only_in_the_dutch_table']}")
    if check.get("only_in_this_language"):
        print(f"  extra here:   {check['only_in_this_language']}")
    for un in sorted(names)[:3]:
        print(f"  UN {un}: {names[un]}")

    if check.get("agreement") is None or check["agreement"] < args.min_agreement:
        print(f"\nAgreement {check.get('agreement')} is below {args.min_agreement}: "
              "the reading is wrong. Nothing is written.")
        return 1

    payload = {
        "_comment": (f"Proper shipping names from column (2) of ADR table A, "
                     f"language {args.language}, read by machine with "
                     f"scripts/extract_adr_names_multilingual.py. A compilation "
                     f"of facts offered as an aid; the published text of the ADR "
                     f"remains authoritative."),
        "edition": args.edition,
        "language": args.language,
        "source": (f"{args.edition}, official UNECE edition — table A of chapter "
                   f"3.2, column (2)"),
        "summary": {"un_numbers": len(names), "rows": counts["rows"],
                    "table_pages": counts["table_pages"]},
        "cross_check": check,
        "names": {un: names[un] for un in sorted(names)},
    }
    document = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    print(f"\n{len(names)} UN numbers, {len(document.encode('utf-8'))} bytes")

    if args.dry_run:
        print("Dry run; nothing is written.")
        return 0
    out = args.out or SEED / f"adr_names_{args.language}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover - command line
    raise SystemExit(main())
