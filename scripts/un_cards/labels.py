"""Hazard label diamonds, drawn as vectors — no extracted third-party images.

Each label is drawn from scratch to the layout of the models in ADR 5.2.2.2.2
(shared by RID, ADN and the IMDG Code): a square standing on a corner, the
class colour, a symbol in the upper half and the class or division number in
the bottom corner. The symbols are simplified vector renderings of the
official pictograms — flame, flame over circle, skull and crossbones, gas
cylinder, exploding bomb, corrosion, trefoil, class 9 stripes — kept
recognisable at the 20 mm the card prints them at. They are drawings of the
public label models, not copies of anyone's artwork.

Only the *choice* of which labels to draw comes from data: the label codes in
column (5) of the measured tables. This module never decides that a substance
carries a label; it only knows what each label looks like.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, black, white
from reportlab.lib.utils import ImageReader

#: Official label model artwork, cropped from the UNECE English ADR 2025
#: Volume I (5.2.2.2.2) by scripts/extract_adr_label_models.py and committed
#: by the "Extract UN card assets" workflow. When a model's crop exists it is
#: used as-is; the vector drawings below remain the fallback for codes the
#: crop set does not cover (and for the marks that live outside 5.2.2.2.2).
ASSETS = Path(__file__).resolve().parent / "assets" / "labels"


def _asset(code: str) -> Path | None:
    path = ASSETS / f"{code.replace('.', '_')}.png"
    return path if path.exists() else None

ORANGE = Color(0.93, 0.48, 0.05)
RED = Color(0.79, 0.08, 0.10)
GREEN = Color(0.0, 0.48, 0.24)
YELLOW = Color(0.99, 0.80, 0.01)
BLUE = Color(0.0, 0.33, 0.65)


def _diamond_path(c, cx, cy, half, inset=0.0):
    p = c.beginPath()
    p.moveTo(cx, cy + half - inset)
    p.lineTo(cx + half - inset, cy)
    p.lineTo(cx, cy - half + inset)
    p.lineTo(cx - half + inset, cy)
    p.close()
    return p


def _clip_diamond(c, cx, cy, half):
    c.clipPath(_diamond_path(c, cx, cy, half), stroke=0, fill=0)


def _tongue(c, cx, cy, w, h):
    """One teardrop flame tongue, tip up, base rounded."""
    p = c.beginPath()
    p.moveTo(cx, cy + h)
    p.curveTo(cx + 0.9 * w, cy + 0.40 * h, cx + w, cy - 0.30 * h, cx, cy - 0.55 * h)
    p.curveTo(cx - w, cy - 0.30 * h, cx - 0.9 * w, cy + 0.40 * h, cx, cy + h)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _flame(c, cx, cy, s, color=black):
    """A three-tongue flame: tall centre, two shorter tongues leaning out."""
    c.setFillColor(color)
    _tongue(c, cx - 0.20 * s, cy - 0.06 * s, 0.11 * s, 0.30 * s)
    _tongue(c, cx + 0.20 * s, cy - 0.04 * s, 0.11 * s, 0.34 * s)
    _tongue(c, cx, cy, 0.16 * s, 0.55 * s)


def _flame_over_circle(c, cx, cy, s):
    _flame(c, cx, cy + 0.16 * s, 0.62 * s)
    c.setStrokeColor(black)
    c.setLineWidth(0.075 * s)
    c.circle(cx, cy - 0.34 * s, 0.17 * s, stroke=1, fill=0)


def _skull(c, cx, cy, s):
    c.setFillColor(black)
    # Cranium and jaw.
    c.circle(cx, cy + 0.16 * s, 0.26 * s, stroke=0, fill=1)
    c.rect(cx - 0.14 * s, cy - 0.16 * s, 0.28 * s, 0.14 * s, stroke=0, fill=1)
    # Eyes and nose in the background colour.
    c.setFillColor(white)
    c.circle(cx - 0.10 * s, cy + 0.18 * s, 0.065 * s, stroke=0, fill=1)
    c.circle(cx + 0.10 * s, cy + 0.18 * s, 0.065 * s, stroke=0, fill=1)
    p = c.beginPath()
    p.moveTo(cx, cy + 0.10 * s)
    p.lineTo(cx - 0.035 * s, cy + 0.02 * s)
    p.lineTo(cx + 0.035 * s, cy + 0.02 * s)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    # Crossbones.
    c.setStrokeColor(black)
    c.setLineWidth(0.09 * s)
    c.setLineCap(1)
    c.line(cx - 0.30 * s, cy - 0.34 * s, cx + 0.30 * s, cy - 0.14 * s)
    c.line(cx - 0.30 * s, cy - 0.14 * s, cx + 0.30 * s, cy - 0.34 * s)
    c.setLineCap(0)


def _cylinder(c, cx, cy, s, color=white):
    c.setFillColor(color)
    c.roundRect(cx - 0.13 * s, cy - 0.34 * s, 0.26 * s, 0.58 * s, 0.10 * s, stroke=0, fill=1)
    c.rect(cx - 0.05 * s, cy + 0.22 * s, 0.10 * s, 0.10 * s, stroke=0, fill=1)
    c.rect(cx - 0.09 * s, cy + 0.30 * s, 0.18 * s, 0.05 * s, stroke=0, fill=1)


def _bomb_burst(c, cx, cy, s):
    c.setFillColor(black)
    c.circle(cx, cy - 0.05 * s, 0.17 * s, stroke=0, fill=1)
    c.setStrokeColor(black)
    c.setLineWidth(0.05 * s)
    for dx, dy in ((-0.32, 0.30), (0.0, 0.42), (0.32, 0.30),
                   (-0.42, 0.02), (0.42, 0.02), (-0.26, -0.30), (0.26, -0.30)):
        c.line(cx + 0.4 * dx * s, cy - 0.05 * s + 0.4 * dy * s,
               cx + dx * s, cy - 0.05 * s + dy * s)


def _corrosion(c, cx, cy, s):
    c.setFillColor(black)
    c.setStrokeColor(black)
    for dx, tilt in ((-0.24 * s, 22), (0.20 * s, -22)):
        c.saveState()
        c.translate(cx + dx, cy + 0.24 * s)
        c.rotate(tilt)
        c.rect(-0.065 * s, -0.17 * s, 0.13 * s, 0.34 * s, stroke=0, fill=1)
        c.restoreState()
        # The liquid pouring out of each tube.
        c.setLineWidth(0.035 * s)
        for offset in (-0.05, 0.0, 0.05):
            c.line(cx + dx + offset * s, cy + 0.04 * s,
                   cx + dx + offset * s * 0.6, cy - 0.22 * s)
    # The surfaces being attacked.
    c.rect(cx - 0.42 * s, cy - 0.32 * s, 0.36 * s, 0.06 * s, stroke=0, fill=1)
    c.rect(cx + 0.06 * s, cy - 0.32 * s, 0.36 * s, 0.06 * s, stroke=0, fill=1)


def _trefoil(c, cx, cy, s):
    c.setFillColor(black)
    c.circle(cx, cy, 0.075 * s, stroke=0, fill=1)
    for angle in (90, 210, 330):
        c.saveState()
        c.translate(cx, cy)
        c.rotate(angle)
        p = c.beginPath()
        p.moveTo(0.11 * s, 0)
        p.arcTo(-0.34 * s, -0.34 * s, 0.34 * s, 0.34 * s, startAng=-30, extent=60)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.restoreState()


def _stripes_9(c, cx, cy, half):
    """Seven vertical stripes in the upper half of the class 9 label."""
    c.saveState()
    _clip_diamond(c, cx, cy, half)
    c.setFillColor(black)
    width = half / 7.0
    for i in range(-3, 4):
        if i % 2 == 0:
            c.rect(cx + i * width - width / 2, cy, width, half, stroke=0, fill=1)
    c.restoreState()


def _battery_9a(c, cx, cy, s):
    c.setFillColor(black)
    c.rect(cx - 0.26 * s, cy - 0.30 * s, 0.52 * s, 0.20 * s, stroke=0, fill=1)
    c.rect(cx - 0.18 * s, cy - 0.09 * s, 0.09 * s, 0.05 * s, stroke=0, fill=1)
    c.rect(cx + 0.09 * s, cy - 0.09 * s, 0.09 * s, 0.05 * s, stroke=0, fill=1)


def _stripes_41(c, cx, cy, half):
    """The class 4.1 field: seven red stripes over the whole white diamond."""
    c.saveState()
    _clip_diamond(c, cx, cy, half)
    c.setFillColor(RED)
    width = 2 * half / 9.0
    for i in range(-4, 5):
        if i % 2 == 0:
            c.rect(cx + i * width - width / 2, cy - half, width, 2 * half, stroke=0, fill=1)
    c.restoreState()


def _half_fill(c, cx, cy, half, top_color, bottom_color):
    c.saveState()
    _clip_diamond(c, cx, cy, half)
    c.setFillColor(top_color)
    c.rect(cx - half, cy, 2 * half, half, stroke=0, fill=1)
    c.setFillColor(bottom_color)
    c.rect(cx - half, cy - half, 2 * half, half, stroke=0, fill=1)
    c.restoreState()


def _fish_and_tree(c, cx, cy, s):
    """The environmentally-hazardous / marine-pollutant symbol, simplified:
    a dead fish below a bare tree, as on the 5.2.1.8 mark."""
    c.setFillColor(black)
    c.setStrokeColor(black)
    # The tree: a trunk with two bare branches.
    c.setLineWidth(0.05 * s)
    c.line(cx - 0.22 * s, cy + 0.34 * s, cx - 0.22 * s, cy - 0.02 * s)
    c.line(cx - 0.22 * s, cy + 0.22 * s, cx - 0.36 * s, cy + 0.38 * s)
    c.line(cx - 0.22 * s, cy + 0.12 * s, cx - 0.08 * s, cy + 0.30 * s)
    # The ground line.
    c.setLineWidth(0.04 * s)
    c.line(cx - 0.40 * s, cy - 0.02 * s, cx + 0.05 * s, cy - 0.02 * s)
    # The fish, belly-up: body, tail, eye as a cross would overdo it — a dot.
    p = c.beginPath()
    p.moveTo(cx - 0.02 * s, cy - 0.22 * s)
    p.curveTo(cx + 0.10 * s, cy - 0.10 * s, cx + 0.26 * s, cy - 0.10 * s,
              cx + 0.34 * s, cy - 0.22 * s)
    p.curveTo(cx + 0.26 * s, cy - 0.34 * s, cx + 0.10 * s, cy - 0.34 * s,
              cx - 0.02 * s, cy - 0.22 * s)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    p = c.beginPath()
    p.moveTo(cx + 0.34 * s, cy - 0.22 * s)
    p.lineTo(cx + 0.44 * s, cy - 0.13 * s)
    p.lineTo(cx + 0.44 * s, cy - 0.31 * s)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def draw_label(c, code: str, x: float, y: float, size: float) -> None:
    """Draw the label for one column (5) code in a box of ``size`` points.

    ``x, y`` is the lower-left corner of the bounding box. Codes are drawn as
    the models draw them; a code without a model here falls back to a plain
    diamond carrying the code as text, so an unexpected value stays visible
    instead of vanishing.
    """
    half = size / 2.0
    cx, cy = x + half, y + half
    sym = size  # symbol scale unit
    code = code.strip()

    asset = _asset(code)
    if asset is not None:
        c.drawImage(ImageReader(str(asset)), x, y, width=size, height=size,
                    preserveAspectRatio=True, anchor="c", mask="auto")
        return

    background = white
    number_color = black
    symbol = None
    number = code
    compat_text = None

    if code.startswith("1"):
        background = ORANGE
        if code in {"1.4", "1.5", "1.6"}:
            symbol = "big-number"
            number = "1"
            compat_text = code.split(".")[1]
        else:
            symbol = _bomb_burst
            number = "1"
    elif code == "2.1":
        background = RED
        symbol = _flame
        number = "2"
    elif code == "2.2":
        background = GREEN
        symbol = "cylinder"
        number = "2"
    elif code == "2.3":
        background = white
        symbol = _skull
        number = "2"
    elif code == "3":
        background = RED
        symbol = _flame
        number = "3"
    elif code == "4.1":
        background = white
        symbol = _flame
        number = "4"
    elif code == "4.2":
        background = white
        symbol = _flame
        number = "4"
    elif code == "4.3":
        background = BLUE
        symbol = _flame
        number = "4"
        number_color = white
    elif code == "5.1":
        background = YELLOW
        symbol = _flame_over_circle
        number = "5.1"
    elif code == "5.2":
        background = YELLOW
        symbol = _flame
        number = "5.2"
    elif code == "6.1":
        background = white
        symbol = _skull
        number = "6"
    elif code.startswith("7"):
        background = white
        symbol = _trefoil
        number = "7"
    elif code == "8":
        background = white
        symbol = _corrosion
        number = "8"
        number_color = white
    elif code in {"9", "9A"}:
        background = white
        symbol = "stripes9"
        number = "9"
    elif code == "MP":
        # The marine pollutant / environmentally hazardous mark: no class
        # number in the bottom corner, only the fish-and-tree symbol.
        background = white
        symbol = "fish"
        number = ""

    # Field.
    c.saveState()
    c.setFillColor(background)
    c.setStrokeColor(black)
    c.setLineWidth(0.9)
    c.drawPath(_diamond_path(c, cx, cy, half), stroke=1, fill=1)
    # Inner line, as the models have.
    c.setLineWidth(0.5)
    c.drawPath(_diamond_path(c, cx, cy, half, inset=0.06 * size), stroke=1, fill=0)

    if code == "4.1":
        _stripes_41(c, cx, cy, half)
    if code == "4.2":
        _half_fill(c, cx, cy, half, white, RED)
    if code == "5.2":
        _half_fill(c, cx, cy, half, RED, YELLOW)
        c.setLineWidth(0.5)
        c.drawPath(_diamond_path(c, cx, cy, half, inset=0.06 * size), stroke=1, fill=0)
    if code == "8":
        _half_fill(c, cx, cy, half, white, black)
    if code.startswith("7"):
        _half_fill(c, cx, cy, half, YELLOW, white)

    symbol_color = white if code in {"2.1", "3", "4.3"} else black
    if symbol == "fish":
        _fish_and_tree(c, cx, cy + 0.04 * size, sym * 0.8)
    elif symbol == "stripes9":
        _stripes_9(c, cx, cy, half)
        if code == "9A":
            _battery_9a(c, cx, cy + 0.02 * size, sym * 0.9)
    elif symbol == "cylinder":
        _cylinder(c, cx, cy + 0.12 * size, sym * 0.75, color=white)
    elif symbol == "big-number":
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", size * 0.34)
        c.drawCentredString(cx, cy + 0.02 * size, code)
    elif symbol is _flame:
        _flame(c, cx, cy + 0.16 * size, sym * 0.62, color=symbol_color)
    elif symbol is _flame_over_circle:
        _flame_over_circle(c, cx, cy + 0.16 * size, sym * 0.55)
    elif symbol is _skull:
        _skull(c, cx, cy + 0.16 * size, sym * 0.62)
    elif symbol is _bomb_burst:
        _bomb_burst(c, cx, cy + 0.16 * size, sym * 0.55)
    elif symbol is _corrosion:
        _corrosion(c, cx, cy + 0.16 * size, sym * 0.62)
    elif symbol is _trefoil:
        _trefoil(c, cx, cy + 0.18 * size, sym * 0.55)
    elif symbol is None:
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", size * 0.16)
        c.drawCentredString(cx, cy + 0.10 * size, code)

    # Compatibility/division text for class 1, e.g. "1.3C" mid-label.
    if code.startswith("1") and symbol is _bomb_burst:
        pass  # the classification code is printed by the card, not the label
    if compat_text:
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", size * 0.13)
        c.drawCentredString(cx, cy - 0.16 * size, compat_text)

    # Class number in the bottom corner.
    if number:
        c.setFillColor(number_color)
        c.setFont("Helvetica-Bold", size * 0.13)
        c.drawCentredString(cx, cy - half + 0.14 * size, number)
    c.restoreState()
