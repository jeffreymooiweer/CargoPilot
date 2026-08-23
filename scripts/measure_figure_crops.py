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

A blob sketch at forty-six characters tells a diamond from a rectangle and no
more, which is enough to pick a candidate and not enough to be sure of it. So a
second mode looks at one chosen box closely, in grey levels rather than ink or
paper:

    python scripts/measure_figure_crops.py --doc adr2 \
        --box "248,222.2,547.2,369.3,660.3"

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


#: Darkest to lightest, for the close look. Ink or paper is enough to find a
#: blob; it is not enough to tell a battery from a flame, and picking the wrong
#: figure is exactly the mistake a crop box carries forward silently.
SHADES = "@%#*+=-:. "


def _closeup(page: Any, rect: list[float], width: int = 104) -> list[str]:
    """One box in grey levels, at whatever resolution fills ``width``.

    Rendered from the page rather than from the 70 dpi mask, so the detail that
    decides which figure this is survives: hatching, a flame's taper, the gap
    between a battery's terminals.
    """
    span_x = max(rect[2] - rect[0], 1.0)
    span_y = max(rect[3] - rect[1], 1.0)
    # Two rendered pixels per character across, and four down, because a
    # terminal cell is about twice as tall as it is wide.
    dpi = max(36, min(300, round(72.0 * width * 2 / span_x)))
    pixmap = page.get_pixmap(dpi=dpi, clip=pymupdf.Rect(rect))
    height = max(1, round(width * span_y / span_x / 2))
    rows: list[str] = []
    for row in range(height):
        line = []
        for col in range(width):
            x0 = col * pixmap.width // width
            x1 = max((col + 1) * pixmap.width // width, x0 + 1)
            y0 = row * pixmap.height // height
            y1 = max((row + 1) * pixmap.height // height, y0 + 1)
            samples = [min(pixmap.pixel(x, y)[:3])
                       for y in range(y0, min(y1, pixmap.height))
                       for x in range(x0, min(x1, pixmap.width))]
            value = min(samples) if samples else 255
            line.append(SHADES[min(len(SHADES) - 1, value * len(SHADES) // 256)])
        rows.append("".join(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", default="adr2")
    parser.add_argument("--pages", help="printed page or range")
    parser.add_argument("--box", action="append", default=[],
                        help="look closely at one box: page,x0,y0,x1,y1")
    parser.add_argument("--max-blobs", type=int, default=8,
                        help="how many of the largest blobs to sketch per page")
    parser.add_argument("--min-side", type=float, default=MIN_SIDE_PT,
                        help="ignore blobs narrower or shorter than this, in points")
    args = parser.parse_args()
    min_side = args.min_side

    if args.doc not in SOURCES:
        print(f"{args.doc}: not a known document id", file=sys.stderr)
        return 1
    if not args.pages and not args.box:
        print("give --pages to find boxes, or --box to look at one", file=sys.stderr)
        return 1

    document = pymupdf.open(fetch(args.doc))

    if args.box:
        print(SOURCES[args.doc]["title"])
        print("=" * 78)
        for spec in args.box:
            parts = [part.strip() for part in spec.split(",")]
            if len(parts) != 5:
                print(f"{spec}: expected page,x0,y0,x1,y1", file=sys.stderr)
                return 1
            number = int(parts[0])
            rect = [float(part) for part in parts[1:]]
            print(f'\n  "page": {number}, "rect": {rect}')
            for line in _closeup(document[number - 1], rect):
                print(f"    {line}")
        return 0

    first, _, last = args.pages.partition("-")
    start, end = int(first), int(last or first)

    # Everything the run found, repeated compactly at the end. The sketches
    # are the point of this script and they are also long, and a run log is
    # read from its tail — a page that sketches thirty blobs pushes its own
    # candidate list out of reach of the only view there is.
    recap: list[str] = []
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
            if (rect[2] - rect[0]) < min_side or (rect[3] - rect[1]) < min_side:
                continue
            candidates.append({"box": box, "rect": rect,
                               "area": (rect[2] - rect[0]) * (rect[3] - rect[1])})
        candidates.sort(key=lambda item: -item["area"])

        print(f"\n[page {number}] {len(candidates)} candidate(s) over "
              f"{min_side:.0f} pt")
        # A blob without its caption is an unattributed picture, and a page
        # that prints two figures of the same thing — the orientation arrows
        # are drawn twice, framed and unframed — cannot be told apart by shape
        # at all. So the captions go in the log with their own vertical
        # position, and a blob is attributed by where it sits between them.
        captions = [
            (round(block[1], 1), " ".join(block[4].split()))
            for block in page.get_text("blocks")
            if block[4].strip().startswith("Figure")
        ]
        for top, text in sorted(captions):
            print(f"    caption at y={top}: {text}")
            recap.append(f"  [page {number}] caption at y={top}: {text}")
        for entry in candidates[:args.max_blobs]:
            rect = entry["rect"]
            recap.append(f'  [page {number}] "rect": [{rect[0]}, {rect[1]}, '
                         f'{rect[2]}, {rect[3]}]   '
                         f'({rect[2] - rect[0]:.0f} x {rect[3] - rect[1]:.0f} pt)')
        for entry in candidates[:args.max_blobs]:
            rect = entry["rect"]
            print(f'\n  "page": {number}, "rect": [{rect[0]}, {rect[1]}, '
                  f'{rect[2]}, {rect[3]}]   '
                  f'({rect[2] - rect[0]:.0f} x {rect[3] - rect[1]:.0f} pt)')
            for line in _sketch(mask, entry["box"]):
                print(f"    {line}")

    print("\n" + "=" * 78)
    print("Everything found, in one place — captions in page order, then boxes:")
    for line in recap:
        print(line)

    print("\n" + "-" * 78)
    print("Read the sketches, decide which blob is the figure, and put its box")
    print("into scripts/un_cards/assets/label_crops.json. Nothing is committed")
    print("here: a crop nobody looked at is a crop nobody measured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
