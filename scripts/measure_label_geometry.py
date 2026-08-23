#!/usr/bin/env python3
"""Settle what "100 mm x 100 mm" means for a diamond, by measuring the figure.

The provisions give a number without saying which distance it is. ADR
5.2.2.2.1.1.2 says a label "shall be in the form of a square set at an angle of
45 degrees (diamond-shaped)" and that "the minimum dimensions shall be
100 mm x 100 mm". Two readings survive that sentence:

* the **square's side** is 100 mm, so the diamond measures about 141 mm from
  point to point; or
* the **bounding box** is 100 mm, so each side is about 71 mm.

The difference is not academic. It decides how many labels fit on an A4 sheet,
and printing the wrong one produces a label that is the wrong size on every
package — the worst failure this feature could have, because it looks right.

Nothing here is decided from memory or from what suppliers happen to sell. The
figures are drawn as vector art in the official PDFs, so the shapes can be
measured rather than interpreted, and the reading is calibrated against a
**known case** before it is applied to the unknown one:

* the **battery mark** (ADR 5.2.1.9.2, IMDG 5.2.1.8) is a *rectangle*, and its
  text says in as many words "a minimum of 100 mm wide x 100 mm high". Its
  figure carries the same "Minimum dimension 100 mm" annotations as the
  diamonds. So whatever those annotations span on the rectangle is what the
  annotation convention means;
* the **environmentally hazardous / marine pollutant mark** and the
  **class label** are the diamonds the answer is wanted for.

Run it on a runner, where the documents can be reached:

    python scripts/measure_label_geometry.py --doc adr2 --pages 247-252

It commits nothing and writes nothing into the repository. It prints
measurements; a human reads them and, if they settle the question, the value
goes into seed/dg/package_marking.json through a reviewed change.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys
from collections import defaultdict
from typing import Any

try:
    import pymupdf
except ImportError:  # pragma: no cover - the runner installs it
    print("PyMuPDF is required: pip install pymupdf", file=sys.stderr)
    raise SystemExit(2)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from read_land_regulations import SOURCES, fetch  # noqa: E402

#: Two segments count as one shape when their endpoints are this close, in
#: points. The figures are drawn at page scale, where a hairline is under half
#: a point, so a tolerance of one point joins a corner without joining two
#: shapes that merely pass near each other.
JOIN_TOLERANCE = 1.0

#: A segment is "diagonal" when its angle is within this many degrees of 45.
#: The diamonds are drawn as exact rotations, but a PDF stores coordinates as
#: decimals and a rounded corner costs a fraction of a degree.
DIAGONAL_TOLERANCE = 3.0


def _segments(page: Any) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Every straight line the page draws, as endpoint pairs in points."""
    found: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l":
                start, end = item[1], item[2]
                found.append(((start.x, start.y), (end.x, end.y)))
            elif item[0] == "re":
                rect = item[1]
                corners = [(rect.x0, rect.y0), (rect.x1, rect.y0),
                           (rect.x1, rect.y1), (rect.x0, rect.y1)]
                for index in range(4):
                    found.append((corners[index], corners[(index + 1) % 4]))
    return found


def _length(segment) -> float:
    (x0, y0), (x1, y1) = segment
    return math.hypot(x1 - x0, y1 - y0)


def _angle(segment) -> float:
    (x0, y0), (x1, y1) = segment
    return abs(math.degrees(math.atan2(y1 - y0, x1 - x0))) % 180


def _is_diagonal(segment) -> bool:
    angle = _angle(segment)
    return (abs(angle - 45) <= DIAGONAL_TOLERANCE
            or abs(angle - 135) <= DIAGONAL_TOLERANCE)


def _cluster(segments) -> list[list]:
    """Group segments into shapes by shared endpoints.

    A union-find over endpoints rounded to the join tolerance. Crude, and
    right for this: the figures are a handful of closed outlines with plenty of
    white space between them.
    """
    parent: dict[int, int] = {}

    def find(node: int) -> int:
        while parent.setdefault(node, node) != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    def key(point) -> tuple[int, int]:
        return (round(point[0] / JOIN_TOLERANCE), round(point[1] / JOIN_TOLERANCE))

    by_point: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, segment in enumerate(segments):
        find(index)
        for point in segment:
            by_point[key(point)].append(index)
    for shared in by_point.values():
        for other in shared[1:]:
            union(shared[0], other)

    groups: dict[int, list] = defaultdict(list)
    for index, segment in enumerate(segments):
        groups[find(index)].append(segment)
    return list(groups.values())


def _bbox(shape) -> tuple[float, float, float, float]:
    xs = [point[0] for segment in shape for point in segment]
    ys = [point[1] for segment in shape for point in segment]
    return min(xs), min(ys), max(xs), max(ys)


def describe(shape) -> dict[str, Any] | None:
    """What a shape is and how big, in points, if it is one we care about."""
    if len(shape) < 4:
        return None
    x0, y0, x1, y1 = _bbox(shape)
    width, height = x1 - x0, y1 - y0
    if width < 20 or height < 20:
        return None

    diagonals = [segment for segment in shape if _is_diagonal(segment)]
    axis_aligned = [segment for segment in shape
                    if _angle(segment) < DIAGONAL_TOLERANCE
                    or abs(_angle(segment) - 90) < DIAGONAL_TOLERANCE]

    if len(diagonals) >= 4 and len(diagonals) >= len(axis_aligned):
        sides = sorted(_length(segment) for segment in diagonals)[:4]
        side = sum(sides) / len(sides)
        return {
            "kind": "diamond",
            "bbox_width_pt": width,
            "bbox_height_pt": height,
            "mean_side_pt": side,
            # A true 45-degree square satisfies bbox = side * sqrt(2). Printing
            # the ratio shows whether the drawing really is one, or whether the
            # cluster caught something else.
            "bbox_over_side": width / side if side else 0.0,
            "segments": len(shape),
        }
    if len(axis_aligned) >= 4 and not diagonals:
        return {
            "kind": "rectangle",
            "bbox_width_pt": width,
            "bbox_height_pt": height,
            "segments": len(shape),
        }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", default="adr2",
                        help="document id from seed/dg/sources.json")
    parser.add_argument("--pages", required=True,
                        help="printed page or range, e.g. 247-252")
    args = parser.parse_args()

    first, _, last = args.pages.partition("-")
    start, end = int(first), int(last or first)

    if args.doc not in SOURCES:
        print(f"{args.doc}: not a known document id", file=sys.stderr)
        return 1
    document = pymupdf.open(fetch(args.doc))
    print(SOURCES[args.doc]["title"])
    print("=" * 78)
    print("All sizes in PDF points (1 pt = 1/72 inch). What matters is not the")
    print("absolute size but the ratio bbox/side, and how a shape compares with")
    print("the battery mark, whose text fixes it at 100 mm wide by 100 mm high.")
    print()

    for number in range(start, end + 1):
        index = number - 1
        if index < 0 or index >= document.page_count:
            continue
        page = document[index]
        shapes = [describe(shape) for shape in _cluster(_segments(page))]
        shapes = [shape for shape in shapes if shape]
        if not shapes:
            continue
        text = page.get_text()
        annotated = "Minimum dimension" in text
        print(f"[page {number}] {len(shapes)} shape(s); "
              f"'Minimum dimension' on the page: {annotated}")
        for shape in sorted(shapes, key=lambda s: -s["bbox_width_pt"])[:6]:
            if shape["kind"] == "diamond":
                print(f"    diamond  bbox {shape['bbox_width_pt']:.1f} x "
                      f"{shape['bbox_height_pt']:.1f} pt, mean side "
                      f"{shape['mean_side_pt']:.1f} pt, bbox/side "
                      f"{shape['bbox_over_side']:.3f} "
                      f"({shape['segments']} segments)")
            else:
                print(f"    rectangle bbox {shape['bbox_width_pt']:.1f} x "
                      f"{shape['bbox_height_pt']:.1f} pt "
                      f"({shape['segments']} segments)")
        print()

    print("-" * 78)
    print("How to read this. Find the battery mark's rectangle, whose text says")
    print("100 mm wide x 100 mm high, and note its width in points. Then find")
    print("the diamond on the same or a neighbouring figure page. If the")
    print("diamond's *bounding box* is about that same width, then 100 mm is")
    print("the bounding box and each side is about 71 mm. If the diamond's")
    print("*side* is about that width, then 100 mm is the side and the diamond")
    print("is about 141 mm from point to point.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
