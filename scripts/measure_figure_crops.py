#!/usr/bin/env python3
"""Find the crop box of a figure in an official edition, without seeing it.

``scripts/extract_adr_label_models.py`` cuts the hazard label models out of ADR
5.2.2.2.2 against boxes pinned in ``scripts/un_cards/assets/label_crops.json``.
Those boxes were measured once, by ink-blob detection over renders of the table
pages. Two figures the package label sheet wants were never measured that way:
the **battery mark** of 5.2.1.9.2 and the **orientation arrows** of 5.2.1.10.1.
This is the measuring half for those, and for any figure after them.

The awkward part is that the measurement happens on a runner and the result is
read from a run log — the artefacts cannot be fetched back through the
development container's proxy. So this does not merely print coordinates, which
tell a reader nothing about *which* blob they found. It prints an ASCII sketch
of every candidate at a few dozen characters across, which is enough to tell a
diamond from a rectangle, a pair of arrows from a table cell, and hatched
edging from a plain border.

    python scripts/measure_figure_crops.py --doc adr2 --pages 248-249

Nothing is committed. A human reads the sketches, decides which blob is the
figure, and the chosen box goes into label_crops.json through a reviewed change
— the same route the twenty-three existing models took.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

try:
    import pymupdf
except ImportError:  # pragma: no cover - the runner installs it
    print("PyMuPDF is required: pip install pymupdf", file=sys.stderr)
    raise SystemExit(2)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from read_land_regulations import SOURCES, fetch  # noqa: E402

#: The render resolution the existing crop boxes were measured at, so a box
#: found here lands in the same coordinate space as the twenty-three already
#: pinned. Changing it would silently move every future crop relative to them.
DPI = 70

#: A pixel counts as ink below this, measured on the *darkest* channel rather
#: than on any single one. The first version of this read channel 0, which is
#: red — and red ink has a high red value, so it read as paper. That made the
#: battery mark of 5.2.1.9.2, whose edging is hatched in red, invisible to a
#: detector looking straight at it. Anything printed in colour would have gone
#: the same way, which for a chapter about coloured labels is the whole subject.
INK = 200

#: Blobs smaller than this in points are furniture: rule lines, page numbers,
#: the stray marks a scan leaves. The figures wanted here are all well over an
#: inch across.
MIN_SIDE_PT = 30.0


def _blobs(mask: list[list[bool]]) -> list[tuple[int, int, int, int]]:
    """Connected ink regions as pixel boxes, by flood fill.

    Deliberately simple: an iterative four-way fill over a boolean grid. The
    pages are a few hundred pixels across at 70 dpi, so the cost is nothing and
    the behaviour is obvious — which matters more here than speed, because a
    clever region merge would be the thing hiding a wrong box.
    """
    height, width = len(mask), len(mask[0]) if mask else 0
    seen = [[False] * width for _ in range(height)]
    found: list[tuple[int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or seen[y][x]:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            x0 = x1 = x
            y0 = y1 = y
            while stack:
                cx, cy = stack.pop()
                x0, x1 = min(x0, cx), max(x1, cx)
                y0, y1 = min(y0, cy), max(y1, cy)
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height \
                            and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            found.append((x0, y0, x1, y1))
    return found


def _sketch(mask: list[list[bool]], box: tuple[int, int, int, int],
            width: int = 46) -> list[str]:
    """The blob as coarse text, so a run log can show what was found.

    Two characters per cell, because a terminal cell is about twice as tall as
    it is wide and a diamond drawn one-to-one comes out looking like a lozenge.
    """
    x0, y0, x1, y1 = box
    span_x = max(x1 - x0 + 1, 1)
    span_y = max(y1 - y0 + 1, 1)
    height = max(1, round(width * span_y / span_x / 2))
    rows: list[str] = []
    for row in range(height):
        line = []
        for col in range(width):
            sx0 = x0 + col * span_x // width
            sx1 = x0 + (col + 1) * span_x // width
            sy0 = y0 + row * span_y // height
            sy1 = y0 + (row + 1) * span_y // height
            inked = any(mask[y][x]
                        for y in range(sy0, max(sy1, sy0 + 1))
                        for x in range(sx0, max(sx1, sx0 + 1))
                        if 0 <= y < len(mask) and 0 <= x < len(mask[0]))
            line.append("#" if inked else ".")
        rows.append("".join(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", default="adr2")
    parser.add_argument("--pages", required=True, help="printed page or range")
    parser.add_argument("--max-blobs", type=int, default=8,
                        help="how many of the largest blobs to sketch per page")
    args = parser.parse_args()

    if args.doc not in SOURCES:
        print(f"{args.doc}: not a known document id", file=sys.stderr)
        return 1
    first, _, last = args.pages.partition("-")
    start, end = int(first), int(last or first)

    document = pymupdf.open(fetch(args.doc))
    scale = DPI / 72.0
    print(SOURCES[args.doc]["title"])
    print(f"rendered at {DPI} dpi — the resolution label_crops.json was measured at")
    print("=" * 78)

    for number in range(start, end + 1):
        index = number - 1
        if not (0 <= index < document.page_count):
            continue
        page = document[index]
        pixmap = page.get_pixmap(dpi=DPI)
        mask = [[min(pixmap.pixel(x, y)[:3]) < INK for x in range(pixmap.width)]
                for y in range(pixmap.height)]
        candidates: list[dict[str, Any]] = []
        for box in _blobs(mask):
            x0, y0, x1, y1 = box
            rect = [round(x0 / scale, 1), round(y0 / scale, 1),
                    round((x1 + 1) / scale, 1), round((y1 + 1) / scale, 1)]
            if (rect[2] - rect[0]) < MIN_SIDE_PT or (rect[3] - rect[1]) < MIN_SIDE_PT:
                continue
            candidates.append({"box": box, "rect": rect,
                               "area": (rect[2] - rect[0]) * (rect[3] - rect[1])})
        candidates.sort(key=lambda item: -item["area"])

        print(f"\n[page {number}] {len(candidates)} candidate(s) over "
              f"{MIN_SIDE_PT:.0f} pt")
        for entry in candidates[:args.max_blobs]:
            rect = entry["rect"]
            print(f'\n  "page": {number}, "rect": [{rect[0]}, {rect[1]}, '
                  f'{rect[2]}, {rect[3]}]   '
                  f'({rect[2] - rect[0]:.0f} x {rect[3] - rect[1]:.0f} pt)')
            for line in _sketch(mask, entry["box"]):
                print(f"    {line}")

    print("\n" + "-" * 78)
    print("Read the sketches, decide which blob is the figure, and put its box")
    print("into scripts/un_cards/assets/label_crops.json. Nothing is committed")
    print("here: a crop nobody looked at is a crop nobody measured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
