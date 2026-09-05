"""The page every self-designed document is drawn on.

One frame for the packing list, the placarding sheet, the equipment list, the
stowage plan, the on-board pack and the label sheet: the brand's logo and name
at the top of every page, a rule under it, and the brand with the page number
at the foot. What the documents say is theirs; what they are printed on is
the installation's.
"""
from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate

from app.core.languages import pick
from app.services.documents import brand as brand_module

BRAND_COLOUR = colors.HexColor("#1E3A5F")
RULE = colors.HexColor("#D9E2EC")
MUTED = colors.HexColor("#666666")

#: The logo's box: never taller than this, never wider than this.
LOGO_HEIGHT = 11 * mm
LOGO_WIDTH = 46 * mm
HEADER_HEIGHT = 16 * mm

PAGE = {"nl": "Pagina", "en": "Page", "de": "Seite", "fr": "Page"}


def _draw_frame(canvas: Canvas, doc: SimpleDocTemplate, title: str, lang: str) -> None:
    brand = brand_module.current()
    width, height = doc.pagesize
    left, right = doc.leftMargin, width - doc.rightMargin
    top = height - 10 * mm
    canvas.saveState()

    x = left
    size = brand.logo_size()
    if size and brand.logo:
        ratio = size[0] / max(size[1], 1)
        logo_h = LOGO_HEIGHT
        logo_w = logo_h * ratio
        if logo_w > LOGO_WIDTH:
            logo_w = LOGO_WIDTH
            logo_h = logo_w / max(ratio, 0.01)
        try:
            canvas.drawImage(ImageReader(io.BytesIO(brand.logo)), left, top - logo_h,
                             width=logo_w, height=logo_h, mask="auto",
                             preserveAspectRatio=True, anchor="sw")
            x = left + logo_w + 4 * mm
        except Exception:
            x = left
    canvas.setFillColor(BRAND_COLOUR)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(x, top - 7.5 * mm, brand.name[:60])

    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(right, top - 7.5 * mm, title[:90])

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    rule_y = top - LOGO_HEIGHT - 2.5 * mm
    canvas.line(left, rule_y, right, rule_y)

    foot = 8 * mm
    canvas.line(left, foot + 4 * mm, right, foot + 4 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(left, foot, brand.name[:60])
    canvas.drawRightString(right, foot, f"{pick(PAGE, lang, 'Page')} {doc.page}")
    canvas.restoreState()


def branded_document(out_path: Path | str, title: str, lang: str = "nl",
                     pagesize=A4) -> SimpleDocTemplate:
    """A document whose every page carries the frame."""
    doc = SimpleDocTemplate(
        str(out_path), pagesize=pagesize,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm + HEADER_HEIGHT, bottomMargin=18 * mm,
        title=title, author=brand_module.current().name,
    )

    def on_page(canvas: Canvas, document: SimpleDocTemplate) -> None:
        _draw_frame(canvas, document, title, lang)

    doc.build = _with_frame(doc, on_page)  # type: ignore[method-assign]
    return doc


def _with_frame(doc: SimpleDocTemplate, on_page):
    original = doc.build

    def build(story, **kwargs):
        kwargs.setdefault("onFirstPage", on_page)
        kwargs.setdefault("onLaterPages", on_page)
        return original(story, **kwargs)

    return build
