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
    """Bounding boxes of vector figure clusters big enough to be a label."""
    rects: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        r = drawing["rect"]
        if r.width < 8 or r.height < 8:
            continue
        if r.width > page.rect.width * 0.95:
            continue  # the page frame
        placed = False
        for i, existing in enumerate(rects):
            if fitz.Rect(existing).intersects(r) or (
                    abs(existing.x0 - r.x0) < 30 and abs(existing.y0 - r.y0) < 30):
                rects[i] = fitz.Rect(min(existing.x0, r.x0), min(existing.y0, r.y0),
                                     max(existing.x1, r.x1), max(existing.y1, r.y1))
                placed = True
                break
        if not placed:
            rects.append(fitz.Rect(r))
    return [r for r in rects if 40 <= r.width <= 400 and 40 <= r.height <= 400]


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


def extract(vol1: Path, out_dir: Path) -> dict:
    doc = fitz.open(str(vol1))
    pages = find_section_pages(doc)
    if not pages:
        raise SystemExit("the 5.2.2.2.2 model table was not found")
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"pages": [p + 1 for p in pages], "models": {}}

    # Collect anchors and figures page by page; a figure belongs to the row
    # band of the anchor it vertically overlaps.
    for number in pages:
        page = doc[number]
        anchors = row_anchors(page)
        if not anchors:
            continue
        figures: list[tuple[str, object]] = [("image", ir) for ir in image_rects(page)]
        figures += [("vector", r) for r in drawing_clusters(page)]
        bands = []
        for i, (code, y) in enumerate(anchors):
            y_end = anchors[i + 1][1] if i + 1 < len(anchors) else page.rect.height
            bands.append((code, y - 6, y_end - 6))
        for kind, item in figures:
            rect = item[1] if kind == "image" else item
            centre = (rect.y0 + rect.y1) / 2
            for code, y0, y1 in bands:
                if y0 <= centre < y1 and code not in report["models"]:
                    target = out_dir / f"{code.replace('.', '_')}.png"
                    if kind == "image":
                        xref = item[0]
                        pix = fitz.Pixmap(doc, xref)
                        if pix.n > 4:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                    else:
                        clip = fitz.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
                        pix = page.get_pixmap(clip=clip, dpi=RENDER_DPI)
                    pix = trim_white(pix)
                    pix.save(str(target))
                    report["models"][code] = {
                        "file": target.name, "page": number + 1, "kind": kind,
                        "px": [pix.width, pix.height],
                    }
                    break

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
