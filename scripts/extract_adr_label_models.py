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
    clip = fitz.IRect(left, top, right + 1, bottom + 1)
    if clip.width < 10 or clip.height < 10:
        return pix
    trimmed = fitz.Pixmap(pix.colorspace, clip, pix.alpha)
    trimmed.copy(pix, clip)
    return trimmed


def extract(vol: Path, out_dir: Path) -> dict:
    spec = json.loads(CROPS.read_text(encoding="utf-8"))
    doc = fitz.open(str(vol))
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"document": spec.get("document"), "models": {}, "failed": []}
    for code, entry in spec["crops"].items():
        page = doc[entry["page"] - 1]
        clip = fitz.Rect(entry["rect"])
        pix = trim_white(page.get_pixmap(clip=clip, dpi=RENDER_DPI))
        if pix.width < 100 or pix.height < 100:
            report["failed"].append(
                {"model": code, "reason": f"crop trimmed to {pix.width}x{pix.height}"})
            continue
        target = out_dir / f"{code.replace('.', '_')}.png"
        pix.save(str(target))
        report["models"][code] = {
            "file": target.name, "page": entry["page"], "px": [pix.width, pix.height]}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vol1", required=True, type=Path,
                        help="the UNECE English volume that holds chapter 5.2")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-missing", action="store_true",
                        help="report failures without failing the run")
    args = parser.parse_args()
    report = extract(args.vol1, args.out)
    print(json.dumps(report, indent=2))
    if report["failed"] and not args.allow_missing:
        print(f"FAILED MODELS: {[f['model'] for f in report['failed']]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
