"""Crop the hazard label models of ADR 5.2.2.2.2 out of the official edition.

The UN cards must show the real label artwork, and the most official source
that prints every model is the ADR itself: section 5.2.2.2.2 of Volume I
shows each model as an illustration beside its table row. This script finds
those illustrations — embedded images and vector-drawn figures alike — pairs
each with the model number that anchors its table row, and saves one tightly
cropped PNG per model. The artwork is the published label model (public
regulatory signage, language-free); nothing is redrawn or invented here.

Runs on a GitHub runner (the development container cannot reach unece.org):

    python scripts/extract_adr_label_models.py --vol1 adr1.pdf \
        --out scripts/un_cards/assets/labels

It prints a per-model report and exits non-zero when models are missing, so
the workflow fails aloud instead of committing a half set.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

#: Every model number the 5.2.2.2.2 table assigns, in printing order.
MODEL_CODES = [
    "1", "1.4", "1.5", "1.6", "2.1", "2.2", "2.3", "3", "4.1", "4.2", "4.3",
    "5.1", "5.2", "6.1", "6.2", "7A", "7B", "7C", "7D", "7E", "8", "9", "9A",
]

RENDER_DPI = 300


def find_section_pages(doc: fitz.Document) -> list[int]:
    """The pages that *are* the model table, not pages that merely cite it.

    Plenty of special provisions reference 5.2.2.2.2 in passing; a table page
    is recognised by its own repeated column header ("Model No." in the UNECE
    English print, "Model nr." in the official Dutch print) together with at
    least one model code anchored in the first column. The table is one
    contiguous run of such pages; the longest run wins.
    """
    def normalised(number: int) -> str:
        return " ".join(doc[number].get_text().split()).lower()

    table_pages = [
        number for number in range(doc.page_count)
        if ("model no" in normalised(number) or "model nr" in normalised(number))
        and row_anchors(doc[number])
    ]
    runs: list[list[int]] = []
    for number in table_pages:
        if runs and number - runs[-1][-1] <= 2:
            runs[-1].append(number)
        else:
            runs.append([number])
    if not runs:
        # Say what was seen, so a layout change is diagnosable from the log.
        with_header = [n + 1 for n in range(doc.page_count)
                       if "model no" in normalised(n) or "model nr" in normalised(n)]
        with_anchors = [n + 1 for n in range(doc.page_count) if len(row_anchors(doc[n])) >= 3]
        print(f"DIAGNOSTIC pages with a Model header: {with_header[:20]}")
        print(f"DIAGNOSTIC pages with >=3 model-code anchors: {with_anchors[:20]}")
        return []
    best = max(runs, key=len)
    return list(range(best[0], best[-1] + 1))


def row_anchors(page: fitz.Page) -> list[tuple[str, float]]:
    """(model code, y) for every model number printed in the first column."""
    anchors = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        if word in MODEL_CODES and x0 < page.rect.width * 0.25:
            anchors.append((word, y0))
    # The first column can repeat a code (division column prints it again at
    # a similar x on narrow layouts); keep the first occurrence per y-band.
    anchors.sort(key=lambda a: a[1])
    kept: list[tuple[str, float]] = []
    for code, y in anchors:
        if kept and abs(kept[-1][1] - y) < 8:
            continue
        kept.append((code, y))
    return kept


def drawing_clusters(page: fitz.Page) -> list[fitz.Rect]:
    """Bounding boxes of vector figure clusters big enough to be a label.

    A label model prints as dozens of small vector pieces; they are merged by
    proximity (union-find on rects grown by a few points) rather than by
    strict overlap, because the pieces of one diamond touch only loosely.
    """
    pieces = []
    for drawing in page.get_drawings():
        r = fitz.Rect(drawing["rect"])
        if r.width < 2 and r.height < 2:
            continue
        if r.width > page.rect.width * 0.95 and r.height > page.rect.height * 0.9:
            continue  # the page frame
        pieces.append(r)

    parent = list(range(len(pieces)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    grown = [fitz.Rect(r.x0 - 6, r.y0 - 6, r.x1 + 6, r.y1 + 6) for r in pieces]
    for i in range(len(pieces)):
        for j in range(i + 1, len(pieces)):
            if grown[i].intersects(grown[j]) and find(i) != find(j):
                parent[find(i)] = find(j)

    clusters: dict[int, fitz.Rect] = {}
    for i, r in enumerate(pieces):
        root = find(i)
        if root in clusters:
            c = clusters[root]
            clusters[root] = fitz.Rect(min(c.x0, r.x0), min(c.y0, r.y0),
                                       max(c.x1, r.x1), max(c.y1, r.y1))
        else:
            clusters[root] = fitz.Rect(r)
    return [r for r in clusters.values()
            if 30 <= r.width <= 380 and 30 <= r.height <= 380]


def image_rects(page: fitz.Page) -> list[tuple[int, fitz.Rect]]:
    out = []
    for img in page.get_images(full=True):
        xref = img[0]
        for rect in page.get_image_rects(xref):
            if rect.width >= 30 and rect.height >= 30:
                out.append((xref, rect))
    return out


def trim_white(pix: fitz.Pixmap) -> fitz.Pixmap:
    """Cut the white margin off a rendered crop."""
    width, height, n = pix.width, pix.height, pix.n
    samples = pix.samples
    def row_blank(y):
        row = samples[y * width * n:(y + 1) * width * n]
        return all(b > 245 for b in row)
    def col_blank(x):
        return all(all(b > 245 for b in samples[(y * width + x) * n:(y * width + x) * n + n])
                   for y in range(0, height, max(1, height // 200)))
    top = 0
    while top < height - 1 and row_blank(top):
        top += 1
    bottom = height - 1
    while bottom > top and row_blank(bottom):
        bottom -= 1
    left = 0
    while left < width - 1 and col_blank(left):
        left += 1
    right = width - 1
    while right > left and col_blank(right):
        right -= 1
    clip = fitz.IRect(left, top, right + 1, bottom + 1)
    if clip.width < 10 or clip.height < 10:
        return pix
    trimmed = fitz.Pixmap(pix.colorspace, clip, pix.alpha)
    trimmed.copy(pix, clip)
    return trimmed


def _figure_column(page: fitz.Page, previous: tuple[float, float] | None
                   ) -> tuple[float, float] | None:
    """The x-range of the table's figure column, from its own header words.

    The header repeats on every table page ("Figure in bottom corner", Dutch
    "Figuur in benedenhoek"); the column runs from there to the next header
    ("Note") or the right margin. When a continuation page omits the header,
    the previous page's answer carries over.
    """
    figure_x = note_x = None
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        lowered = word.lower().rstrip(".:")
        if lowered in {"figure", "figuur"} and figure_x is None:
            figure_x = x0
        if lowered in {"note", "opmerking"} and note_x is None and x0 > (figure_x or 0):
            note_x = x0
    if figure_x is None:
        return previous
    right = note_x - 4 if note_x else page.rect.width - 18
    return (figure_x - 10, right)


def extract(vol1: Path, out_dir: Path) -> dict:
    doc = fitz.open(str(vol1))
    pages = find_section_pages(doc)
    if not pages:
        raise SystemExit("the 5.2.2.2.2 model table was not found")
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"pages": [p + 1 for p in pages], "models": {}}

    # The figure prints however the edition's typesetter drew it — embedded
    # image, vector art, or a form object — so nothing is detected: the
    # figure *column* of each row band is rendered as a page region and the
    # white margin trimmed off. What the page shows is what the crop holds.
    # Low-resolution page renders ride along under _debug/ so a mismatch can
    # be *seen* instead of re-derived from counters; the directory is removed
    # once the crop set is accepted.
    debug_dir = out_dir / "_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    column: tuple[float, float] | None = None
    for number in pages:
        page = doc[number]
        doc[number].get_pixmap(dpi=70).save(str(debug_dir / f"page_{number + 1}.png"))
        anchors = row_anchors(page)
        column = _figure_column(page, column)
        if not anchors or column is None:
            print(f"DIAGNOSTIC page {number + 1}: anchors="
                  f"{[a[0] for a in anchors]} column={column} — skipped")
            continue

        # One band per model: consecutive repeats of the same code (the
        # figure column prints the class digit too) extend the band rather
        # than splitting it.
        bands: list[tuple[str, float, float]] = []
        for code, y in anchors:
            if bands and bands[-1][0] == code:
                continue
            bands.append((code, y, page.rect.height))
        bands = [(code, y, bands[i + 1][1] - 4 if i + 1 < len(bands) else page.rect.height - 30)
                 for i, (code, y, _) in enumerate(bands)]
        print(f"DIAGNOSTIC page {number + 1}: bands="
              f"{[(c, round(a), round(b)) for c, a, b in bands]} column="
              f"{tuple(round(v) for v in column)}")

        for code, y0, y1 in bands:
            if code in report["models"] or y1 - y0 < 40:
                continue
            clip = fitz.Rect(column[0], y0 - 4, column[1], y1)
            pix = page.get_pixmap(clip=clip, dpi=RENDER_DPI)
            pix = trim_white(pix)
            if pix.width < 60 or pix.height < 60:
                print(f"DIAGNOSTIC {code}: crop trimmed to nothing "
                      f"({pix.width}x{pix.height}) on page {number + 1}")
                continue
            target = out_dir / f"{code.replace('.', '_')}.png"
            pix.save(str(target))
            report["models"][code] = {
                "file": target.name, "page": number + 1, "kind": "region",
                "px": [pix.width, pix.height],
            }

    missing = [c for c in MODEL_CODES if c not in report["models"]]
    report["missing"] = missing
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vol1", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-missing", action="store_true",
                        help="report missing models without failing the run")
    args = parser.parse_args()
    report = extract(args.vol1, args.out)
    print(json.dumps(report, indent=2))
    if report["missing"] and not args.allow_missing:
        print(f"MISSING MODELS: {', '.join(report['missing'])}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
