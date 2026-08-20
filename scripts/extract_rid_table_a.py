#!/usr/bin/env python3
"""Read table A of RID 3.2.1 out of the editions in the regulations store.

The UN cards fail honestly for rail because CargoPilot's table A is the
ADR's: generating a RID card from a road row would relabel road data as
rail data (columns (12) to (20) are the rail's own — tank codes, transport
category, the W/CW/CE provisions, the hazard number can all differ). This
script reads the RID's own table, the way ``extract_rid_shunting_labels.py``
read its column (5): geometrically, from the word positions of the official
editions in the store, with two independent readings before anything
becomes a seed.

Planned readings:

``--pdf RID-2025-NL.pdf``  the Dutch edition (operator-supplied).
``--pdf rid.pdf``          the OTIF English edition, read the same way.

Cross-checks: columns (1)-(7b) against ``adr_table_a.json`` (the regimes
harmonise them), the bracketed shunting models of column (5) against the
reading of v1.123.0, and the two editions against each other on the rail
columns.

The layout is not assumed: ``--probe`` reports what the books actually
print — which pages carry the table's column-number band, which markers
each edition shows, where they stand — and the parser is built on those
measurements, run by run, on the runner (the development container holds
no RID edition).

    python scripts/extract_rid_table_a.py --pdf rid.pdf --probe
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - runner installs it
    fitz = None

STORE = Path(
    os.environ.get("CARGOPILOT_REGULATIONS_DIR")
    or ("/data/regulations" if Path("/data").is_dir()
        else "/tmp/cargopilot-regulations"))

MARKER = re.compile(r"^\((\d{1,2}[ab]?)\)$")
UN_WORD = re.compile(r"^\d{4}$")


def probe(pdf_path: Path, sample_pages: int) -> int:
    doc = fitz.open(str(pdf_path))
    print(f"== {pdf_path.name}: {doc.page_count} pages, "
          f"first page rect {doc[0].rect} ==")
    header_pages: list[tuple[int, tuple[str, ...]]] = []
    for number in range(doc.page_count):
        words = doc[number].get_text("words")
        markers = sorted(
            ((w[0], MARKER.match(w[4]).group(1)) for w in words
             if MARKER.match(w[4])), key=lambda m: m[0])
        codes = tuple(code for _x, code in markers)
        if len(codes) >= 10:
            header_pages.append((number + 1, codes))

    if not header_pages:
        print("no pages with a 10+ column-number band found")
        return 1

    runs: list[list[tuple[int, tuple[str, ...]]]] = []
    for page, codes in header_pages:
        if runs and page - runs[-1][-1][0] <= 2:
            runs[-1].append((page, codes))
        else:
            runs.append([(page, codes)])
    print(f"{len(header_pages)} header pages in {len(runs)} runs:")
    for run in runs:
        print(f"  pages {run[0][0]}-{run[-1][0]} ({len(run)} pages)")
    shapes = Counter(codes for _page, codes in header_pages)
    for codes, count in shapes.most_common(4):
        print(f"  {count} pages with markers: {' '.join(codes)}")

    # The largest run is the table itself; show its first page in the raw.
    main_run = max(runs, key=len)
    for page_number in [main_run[0][0], main_run[len(main_run) // 2][0]][:sample_pages]:
        page = doc[page_number - 1]
        words = page.get_text("words")
        markers = sorted(((w[0], w[1], w[4]) for w in words
                          if MARKER.match(w[4])), key=lambda m: m[0])
        print(f"\n-- page {page_number}: marker positions --")
        print("  " + "  ".join(f"{t}@x{x:.0f}/y{y:.0f}" for x, y, t in markers))
        un_rows = sorted((w[1], w[0], w[4]) for w in words
                         if UN_WORD.match(w[4]) and w[0] < page.rect.width * 0.2)
        print(f"  {len(un_rows)} UN-number words at the left margin; first five:")
        for y, x, text in un_rows[:5]:
            print(f"    UN {text} at x{x:.0f} y{y:.0f}")
        if un_rows:
            y0 = un_rows[0][0]
            y1 = un_rows[1][0] if len(un_rows) > 1 else y0 + 40
            band = sorted((w for w in words if y0 - 12 <= w[1] < y1 - 2),
                          key=lambda w: (round(w[1] / 4), w[0]))
            print("  first row band, words with x:")
            line = "    "
            for w in band:
                token = f"{w[4]}@{w[0]:.0f}"
                if len(line) + len(token) > 100:
                    print(line)
                    line = "    "
                line += token + " "
            print(line)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True,
                        help="filename in the regulations store, or a path")
    parser.add_argument("--probe", action="store_true",
                        help="report the table's printed structure and exit")
    parser.add_argument("--sample-pages", type=int, default=2)
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        pdf_path = STORE / args.pdf
    if not pdf_path.is_file():
        print(f"not in the store: {args.pdf}", file=sys.stderr)
        return 1

    if args.probe:
        return probe(pdf_path, args.sample_pages)
    print("only --probe is implemented so far: the parser is built on what "
          "the probe measures, not on an assumed layout", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
