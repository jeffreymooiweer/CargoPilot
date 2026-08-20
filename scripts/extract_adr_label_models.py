"""Cut the hazard label models of ADR 5.2.2.2.2 out of the official edition.

The UN cards must show the real label artwork, and the most official source
that prints every model is the ADR itself: section 5.2.2.2.2 of Volume II
(UNECE English edition) shows each model as a specimen illustration. The
print rotates the whole table on the page and draws the figures in ways
neither the embedded-image list nor the vector-drawing walk reports, so no
geometry is inferred here: every model's crop box was **measured** — ink-blob
detection over renders of the six table pages, validated against the model
sequence read off those same pages — and pinned in
``scripts/un_cards/assets/label_crops.json`` next to the sha256 the register
pins for the document itself. This script just renders those boxes at high
resolution and trims the white margin.

Runs on a GitHub runner (the development container cannot reach unece.org):

    python scripts/extract_adr_label_models.py --vol1 adr2.pdf \
        --out scripts/un_cards/assets/labels

A new edition never reuses these boxes: the measurement pass is repeated and
the JSON replaced, and a crop that trims to nothing fails the run aloud.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

CROPS = Path(__file__).resolve().parent / "un_cards" / "assets" / "label_crops.json"

RENDER_DPI = 300


def trim_white(pix: fitz.Pixmap) -> fitz.Pixmap:
    """Cut the white margin off a rendered crop."""
    width, height, n = pix.width, pix.height, pix.n
    samples = pix.samples

    def row_blank(y: int) -> bool:
        row = samples[y * width * n:(y + 1) * width * n]
        return all(b > 245 for b in row)

    def col_blank(x: int) -> bool:
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
    new_w = right - left + 1
    new_h = bottom - top + 1
    if new_w < 10 or new_h < 10:
        return pix
    # Slice the sample bytes directly: a clipped render carries a non-zero
    # origin, and Pixmap.copy interprets rectangles in that shifted space —
    # the mismatch shredded every crop into stride garbage once already.
    rows = []
    for y in range(top, bottom + 1):
        start = (y * width + left) * n
        rows.append(samples[start:start + new_w * n])
    return fitz.Pixmap(pix.colorspace, new_w, new_h, b"".join(rows), pix.alpha)


def mask_outside_diamond(pix: fitz.Pixmap) -> fitz.Pixmap:
    """White out everything outside the mark's own diamond.

    The mark of Figure 5.2.1.8.3 is printed with dimension annotations
    hugging its lower edges. Neither the crop box, nor the crop's ink
    extent, nor a diamond pinned in page coordinates drew the boundary in
    the right place — every indirect frame left annotation text standing.
    So the boundary is fitted to what the render itself shows: the upper
    two edges are annotation-free, and with the diamond's 45-degree slope
    each upper row's ink half-width grows by exactly one pixel per row.
    The apex row and the horizontal extremes fix center and half-diagonal,
    and everything outside the fitted diamond — shaved one pixel into the
    outline, so the vertex-hugging arrowheads fall outside too — is
    blanked.
    """
    w, h, n = pix.width, pix.height, pix.n
    s = bytearray(pix.samples)

    def row_extent(y: int) -> tuple[int, int] | None:
        row = s[y * w * n:(y + 1) * w * n:n]
        xs = [x for x in range(w) if row[x] < 200]
        return (xs[0], xs[-1]) if xs else None

    extents = {y: e for y in range(h) if (e := row_extent(y))}
    if not extents:
        return pix
    apex = min(extents)
    # Upper edges only: each row's ink half-width grows by one pixel per
    # row while both 45-degree edges are the row's extremes. The last row
    # where that linear growth still holds is the vertex height — the
    # dimension arrowheads that flank the vertices break the pattern there,
    # so they cannot inflate the fit the way they inflate the horizontal
    # extremes.
    centers: list[float] = []
    half = 0.0
    for y in range(apex + 4, h):
        extent = extents.get(y)
        if extent is None:
            break
        reach = (extent[1] - extent[0]) / 2.0
        if abs(reach - (y - apex)) > 4:
            break
        centers.append((extent[0] + extent[1]) / 2.0)
        half = float(y - apex)
    if half < 20 or not centers:
        return pix
    centers.sort()
    cx = centers[len(centers) // 2]
    cy = apex + half
    shave = 1.0
    for y in range(h):
        dy = abs(y - cy)
        for x in range(w):
            if abs(x - cx) + dy > half - shave:
                i = (y * w + x) * n
                for k in range(n):
                    s[i + k] = 255
    return fitz.Pixmap(pix.colorspace, w, h, bytes(s), pix.alpha)


def rotate_clockwise(pix: fitz.Pixmap) -> fitz.Pixmap:
    """The print rotates the table content 90 degrees; this restores it."""
    w, h, n = pix.width, pix.height, pix.n
    s = pix.samples
    out = bytearray(w * h * n)
    for ys in range(h):
        for xs in range(w):
            di = (xs * h + (h - 1 - ys)) * n
            si = (ys * w + xs) * n
            out[di:di + n] = s[si:si + n]
    return fitz.Pixmap(pix.colorspace, h, w, bytes(out), pix.alpha)


def extract(vol: Path, out_dir: Path) -> dict:
    spec = json.loads(CROPS.read_text(encoding="utf-8"))
    doc = fitz.open(str(vol))
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"document": spec.get("document"), "models": {}, "failed": []}
    for code, entry in spec["crops"].items():
        page = doc[entry["page"] - 1]
        clip = fitz.Rect(entry["rect"])
        pix = page.get_pixmap(clip=clip, dpi=RENDER_DPI)
        if entry.get("diamond"):
            pix = mask_outside_diamond(pix)
        pix = trim_white(pix)
        # The label table pages are printed rotated; a crop from an upright
        # page (the environmentally hazardous mark of 5.2.1.8.3) overrides
        # the document-level rotation with its own.
        rotation = entry.get("rotate_clockwise_degrees",
                             spec.get("rotate_clockwise_degrees"))
        if rotation == 90:
            pix = rotate_clockwise(pix)
        if pix.width < 100 or pix.height < 100:
            report["failed"].append(
                {"model": code, "reason": f"crop trimmed to {pix.width}x{pix.height}"})
            continue
        target = out_dir / f"{code.replace('.', '_')}.png"
        pix.save(str(target))
        report["models"][code] = {
            "file": target.name, "page": entry["page"], "px": [pix.width, pix.height]}
    return report


def debug_render(vol: Path, needle: str, out_dir: Path) -> int:
    """Render every page that mentions ``needle`` at 70 dpi.

    The measurement pass for a new crop box works off these renders: they
    are committed once, the box is measured on them by hand and pinned in
    label_crops.json, and the renders are retired again. Nothing about a
    crop is ever inferred from text geometry — that road failed for the
    label table and is not walked twice.
    """
    doc = fitz.open(str(vol))
    out_dir.mkdir(parents=True, exist_ok=True)
    hits = 0
    for number in range(doc.page_count):
        page = doc[number]
        if needle not in " ".join(page.get_text().split()):
            continue
        target = out_dir / f"page-{number + 1}.png"
        page.get_pixmap(dpi=70).save(str(target))
        print(f"{needle} on printed page {number + 1} -> {target}")
        hits += 1
    if hits == 0:
        print(f"'{needle}' appears on no page of {vol}", file=sys.stderr)
    return 0 if hits else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vol1", required=True, type=Path,
                        help="the UNECE English volume that holds chapter 5.2")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-missing", action="store_true",
                        help="report failures without failing the run")
    parser.add_argument("--debug-find", metavar="TEXT",
                        help="render the pages mentioning TEXT at 70 dpi into "
                             "--out for a measurement pass, instead of cutting")
    args = parser.parse_args()
    if args.debug_find:
        return debug_render(args.vol1, args.debug_find, args.out)
    report = extract(args.vol1, args.out)
    print(json.dumps(report, indent=2))
    if report["failed"] and not args.allow_missing:
        print(f"FAILED MODELS: {[f['model'] for f in report['failed']]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
