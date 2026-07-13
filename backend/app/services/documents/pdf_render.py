"""Genereer nette PDF's voor zelf-ontworpen CargoPilot-documenten met reportlab.

Gebruikt voor documenten zonder officieel invulbaar formulier (paklijst,
afleverbon, IMO MMDGF, VGM, shipping instructions, ADR/ADN). Officiële invulbare formulieren (CMR, IATA,
CIM) worden elders met pypdf ingevuld en niet nagebouwd.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.documents.exporter import (
    DG_PRODUCT_FIELDS,
    _dg_headers,
    _dg_rows,
    _dims,
    _label,
    _lang,
    _option_label,
    _text,
    condition_met,
    resolve_sections,
)

BRAND = colors.HexColor("#1E3A5F")
LIGHT = colors.HexColor("#D9E2EC")
MUTED = colors.HexColor("#666666")
GRID = colors.HexColor("#B0BEC5")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("cp_title", parent=base["Title"], fontSize=16, spaceAfter=4, textColor=BRAND),
        "status": ParagraphStyle("cp_status", parent=base["Normal"], fontSize=9, textColor=BRAND, italic=True),
        "meta": ParagraphStyle("cp_meta", parent=base["Normal"], fontSize=8, textColor=MUTED),
        "section": ParagraphStyle(
            "cp_section", parent=base["Heading2"], fontSize=11, textColor=colors.white, spaceBefore=8, spaceAfter=0
        ),
        "label": ParagraphStyle("cp_label", parent=base["Normal"], fontSize=8.5, textColor=colors.HexColor("#334155")),
        "value": ParagraphStyle("cp_value", parent=base["Normal"], fontSize=9, alignment=TA_LEFT),
        "note": ParagraphStyle("cp_note", parent=base["Normal"], fontSize=8, textColor=MUTED),
        "cell": ParagraphStyle("cp_cell", parent=base["Normal"], fontSize=8, leading=10),
        "cellh": ParagraphStyle("cp_cellh", parent=base["Normal"], fontSize=8, leading=10, textColor=colors.white),
        "fixed": ParagraphStyle("cp_fixed", parent=base["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#1f2937")),
        "disclaimer": ParagraphStyle("cp_disc", parent=base["Normal"], fontSize=7.5, leading=10, textColor=MUTED),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    s = "" if text is None else str(text)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    return Paragraph(s, style)


def _section_header(title: str, styles: dict, width: float) -> Table:
    t = Table([[_p(title, styles["section"])]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _fields_table(rows: list[tuple[str, Any]], styles: dict, width: float) -> Table:
    data = [[_p(label, styles["label"]), _p(value, styles["value"])] for label, value in rows]
    t = Table(data, colWidths=[width * 0.34, width * 0.66])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
    ]))
    return t


def _grid_table(header: list[str], rows: list[list[Any]], styles: dict, width: float) -> Table:
    data = [[_p(h, styles["cellh"]) for h in header]]
    for row in rows:
        data.append([_p(c, styles["cell"]) for c in row])
    t = Table(data, colWidths=[width / len(header)] * len(header), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    return t


def _visible_fields(section: dict, values: dict) -> list[dict]:
    out = []
    for field in section.get("fields", []):
        if (
            field.get("status") == "CONDITIONAL"
            and field.get("condition")
            and not condition_met(field.get("condition"), values)
            and str(values.get(field["key"], "")).strip() == ""
        ):
            continue
        keep = str(values.get(field["key"], "")).strip() != "" or field.get("status") in {
            "USER_REQUIRED",
            "CARRIER_PROVIDED",
            "OPERATIONAL",
            "SIGNATURE_REQUIRED",
        }
        if keep:
            out.append(field)
    return out


def _field_display(field: dict, values: dict, lang: str) -> Any:
    value = values.get(field["key"], "")
    status = field.get("status")
    if field.get("type") == "select" and value not in (None, ""):
        value = _option_label(field, value, lang)
    if status == "SIGNATURE_REQUIRED":
        if field.get("type") == "checkbox":
            return _text("confirmed", lang) if str(value).lower() in {"true", "1", "yes", "ja"} else _text("not_confirmed", lang)
        return f"[{_text('not_prefilled', lang)}]"
    if str(value).strip() == "":
        if status == "CARRIER_PROVIDED":
            return f"[{_text('carrier_provided', lang)}]"
        if status == "OPERATIONAL":
            return f"[{_text('operational', lang)}]"
        return ""
    return value


def _output_path() -> Path:
    fd, temp_name = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    out_path = Path(temp_name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    return out_path


def render_document_pdf(
    document: dict[str, Any],
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
) -> Path:
    lang = _lang(language)
    styles = _styles()
    out_path = _output_path()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=_label(document, lang),
    )
    width = doc.width
    story: list = []

    story.append(_p(_label(document, lang), styles["title"]))
    issue = document.get("issue_status", {}).get(lang)
    if issue:
        story.append(_p(f"{_text('status', lang)}: {issue}", styles["status"]))
    story.append(_p(f"{_text('generated_with', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["meta"]))
    story.append(Spacer(1, 6))

    for section in resolve_sections(document):
        fields = _visible_fields(section, values)
        if not fields:
            continue
        rows = [(_label(f, lang), _field_display(f, values, lang)) for f in fields]
        story.append(KeepTogether([
            _section_header(_label(section, lang), styles, width),
            _fields_table(rows, styles, width),
            Spacer(1, 6),
        ]))

    included = [ln for ln in lines if ln.get("include", True)]
    if included:
        header = _text("line_headers", lang)
        rows = []
        tw = tv = 0.0
        for i, line in enumerate(included, start=1):
            w = line.get("weight_total_kg") or 0
            v = line.get("transport_volume_m3") or 0
            tw += w
            tv += v
            rows.append([
                i, line.get("output_description") or line.get("description"),
                line.get("quantity"), line.get("unit"),
                line.get("weight_total_kg"), line.get("transport_volume_m3"), _dims(line),
            ])
        rows.append(["", _text("totals", lang), "", "", round(tw, 2), round(tv, 3), ""])
        story.append(_section_header(_text("goods", lang), styles, width))
        story.append(_grid_table(header, rows, styles, width))
        story.append(Spacer(1, 6))

    profile = document.get("dg_profile")
    if profile and dangerous_goods:
        header = _dg_headers(profile, lang)
        rows = []
        for entry in dangerous_goods:
            for product in entry.get("products", []):
                rows.append(_dg_rows(profile, entry, product, values, lang))
        story.append(_section_header(f"{_text('dg_table', lang)} ({profile})", styles, width))
        story.append(_grid_table(header, rows, styles, width))
        story.append(Spacer(1, 6))

    for item in document.get("fixed_texts") or []:
        story.append(_p(item.get(lang) or item.get("nl", ""), styles["fixed"]))
        story.append(Spacer(1, 3))

    legal = document.get("legal_reference", {}).get(lang)
    if legal:
        story.append(_p(f"{_text('legal_reference', lang)}: {legal}", styles["note"]))
    note = document.get("signature_note", {}).get(lang)
    if note:
        story.append(_p(note, styles["note"]))

    story.append(Spacer(1, 8))
    story.append(_p(_text("disclaimer", lang), styles["disclaimer"]))

    doc.build(story)
    return out_path
