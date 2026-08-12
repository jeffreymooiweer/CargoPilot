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
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from read_land_regulations import SOURCES, fetch  # noqa: E402
from extract_adr_table_a import (  # noqa: E402
    BODY_BOTTOM,
    MARKER,
    ROW_GAP,
    UN_START,
    class_left,
    join,
    un_and_name,
)

SEED = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg"

#: What the reading is compared against: the Dutch table already in the
#: repository. Two editions of one table in two languages hold the same UN
#: numbers, and a reading that does not is a reading that went wrong.
REFERENCE = SEED / "adr_table_a.json"


#: How many column numbers a page has to show before it is treated as table A.
#: The Dutch extract put all twenty-three above every page; the UNECE volume
#: lays the table across a two-page spread and shows (1) to (11) on the left and
#: the rest on the right, so a page of this edition carries fourteen at most.
#: Three would be enough for what is read here and would also match a page that
#: merely quotes a few column numbers in running text.
MARKERS_NEEDED = 8

#: The three columns a proper shipping name needs, and the whole reason this
#: reader can work on a layout the twenty-three-column one cannot: (1) and (2)
#: are the UN number and the name, and (3a) is only ever consulted for where the
#: name has to stop. All three are on the left-hand page of the spread.
NEEDED = ("1", "2", "3a")


#: Two ways a row of table A can be told from the next one, and the reader picks
#: whichever the document supports.
BY_GAP, BY_UN_NUMBER = "gap", "un_number"


def learn_banding(document, sample: list[int]) -> tuple[str, float]:
    """How rows are separated in *this* typesetting, measured rather than assumed.

    `extract_adr_table_a.ROW_GAP` is 21 points, and that is a fact about the
    Dutch extract and not about the ADR: 7.1 points between the lines of a row,
    14.2 inside a wrapped name, 28.3 between two entries, and nothing at all in
    between. A gap of 21 sits in that emptiness and cuts cleanly.

    The UNECE volume has no such emptiness. It sets the table tightly enough
    that most entries occupy a single line, so the space between two rows is the
    space between two lines and there is nothing to find. Carrying the Dutch
    constant over made UN 0005 swallow the twenty entries after it; measuring a
    cut made no difference at all, because there is no valley to measure.

    What survives in both is the table itself: **a row begins at its UN number**.
    That is why this returns a method and not only a number. Where the gaps are
    genuinely bimodal the gap decides, because the Dutch edition sets the number
    vertically centred — beside the *second* line of a three-line name — and
    splitting on it there would cut rows in half. Where they are not, the UN
    number decides, because nothing else can.
    """
    gaps: list[float] = []
    for index in sample:
        page = document[index]
        top_marker, centres = band_of(page)
        if top_marker is None or not all(n in centres for n in NEEDED):
            continue
        ys = [y for y, _text in name_column(page, top_marker + 10, centres)]
        gaps.extend(round(b - a, 1) for a, b in zip(ys, ys[1:]) if b > a)
    if len(gaps) < 20:
        return BY_UN_NUMBER, ROW_GAP

    gaps.sort()
    body = [gap for gap in gaps if gap >= 3.0]
    if not body:
        return BY_UN_NUMBER, ROW_GAP
    # A valley worth trusting has crowds on both sides of it. A step with two
    # gaps to its left and eight hundred to its right is an outlier, not a
    # boundary, and cutting there merges the whole page into one row.
    best, cut, share = 0.0, ROW_GAP, 0.0
    for position, (a, b) in enumerate(zip(body, body[1:]), start=1):
        step = b - a
        if step > best:
            below = position / len(body)
            if 0.15 <= below <= 0.95:
                best, cut, share = step, (a + b) / 2, below
    if best >= 3.0 and share:
        return BY_GAP, cut
    return BY_UN_NUMBER, ROW_GAP


def band_of(page) -> tuple[float | None, dict[str, float]]:
    """The column numbers on this page, however few of them there are.

    `extract_adr_table_a.marker_band` wants fifteen and reconstructs the rest
    from the (3a)…(20) span, neither of which survives a table split over two
    pages: column (20) is not on this sheet to measure a span against. So the
    band is taken as it comes, and the caller checks it holds what it needs.
    """
    rows: dict[float, dict[str, float]] = defaultdict(dict)
    for x0, y0, x1, _y1, word, *_rest in page.get_text("words"):
        found = MARKER.match(word.strip())
        if found:
            rows[round(y0, 1)][found.group(1)] = (x0 + x1) / 2
    for y in sorted(rows):
        if len(rows[y]) >= MARKERS_NEEDED:
            return y, dict(rows[y])
    return None, {}


def name_column(page, top: float, centres: dict[str, float]):
    """The lines of columns (1) and (2), read character by character.

    Character by character because the UN number and the name run together in
    the text layer — "1098ALLYLALCOHOL" — and the split is made on the four
    digits. Where the name has to stop is measured on the class values
    themselves, as it is for the Dutch table: the number "(3a)" stands centred
    over its cell and the estimate that follows is some points too far left,
    which is enough to cut the last word off a long name.
    """
    right = class_left(page, top, centres["3a"])
    if right is None:
        right = centres["3a"] - (centres["3a"] - centres["2"]) / 2
    lines: list[tuple[float, str]] = []
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
                lines.append((round(line["bbox"][1], 1),
                              "".join(c for _x, c in kept)))
    lines.sort()
    return lines


def read(path: Path) -> tuple[dict[str, list[str]], list[str], dict[str, int]]:
    """The names per UN number, in the order table A gives them."""
    import fitz

    names: dict[str, list[str]] = defaultdict(list)
    problems: list[str] = []
    counts = {"pages": 0, "table_pages": 0, "rows": 0}
    carried: str | None = None

    with fitz.open(path) as document:
        counts["pages"] = document.page_count
        sample = list(range(0, document.page_count,
                            max(1, document.page_count // 40)))
        method, cut = learn_banding(document, sample)
        counts["banding"] = method
        counts["row_gap"] = round(cut, 1)
        for index in range(document.page_count):
            page = document[index]
            top_marker, centres = band_of(page)
            # A page of running text is not a problem, it is most of the book.
            if top_marker is None or not all(n in centres for n in NEEDED):
                continue
            counts["table_pages"] += 1
            top = top_marker + 10

            bands: list[list[str]] = []
            current: list[str] = []
            previous_y: float | None = None
            for y, text in name_column(page, top, centres):
                text = re.sub(r"\s+", " ", text).strip()
                if not text:
                    continue
                if method == BY_GAP:
                    starts = previous_y is not None and y - previous_y > cut
                else:
                    starts = bool(current) and UN_START.match(text) is not None
                if starts:
                    bands.append(current)
                    current = []
                previous_y = y
                current.append(text)
            if current:
                bands.append(current)

            for band in bands:
                number, name = un_and_name({"1": band})
                if number is None:
                    # A name running over the page break belongs to the row that
                    # began at the foot of the page before.
                    if carried and name and names[carried]:
                        names[carried][-1] = join(names[carried][-1], name)
                    continue
                carried = number
                counts["rows"] += 1
                if name and name not in names[number]:
                    names[number].append(name)
    if counts["table_pages"] == 0:
        problems.append("no page in this document carries the column numbers of "
                        "table A — is this the volume that holds chapter 3.2?")
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
        sizes: dict[int, int] = defaultdict(int)
        for _number, band in found:
            sizes[len(band)] += 1
        print("  band sizes: " + ", ".join(
            f"{size}->{count} pages" for size, count in sorted(sizes.items())))
        with_un = sum(1 for index in range(document.page_count)
                      if _re.search(r"^\s*\d{4}\s", document[index].get_text(),
                                    _re.M))
        print(f"  pages whose text has a line starting with four digits: {with_un}")
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
          f"{counts['rows']} rows, {len(names)} UN numbers "
          f"(rows separated by {counts.get('banding')}"
          + (f", cut at {counts.get('row_gap')} points" if counts.get('banding') == 'gap' else '')
          + ")")
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
