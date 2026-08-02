"""AVC-vrachtbrief (binnenlands wegvervoer) als PDF.

Nagebouwd naar het standaardformulier van sVa / Stichting Vervoeradres: links
de vrachtbrief zelf, rechts het ontvangstbewijs, met dezelfde vakindeling
(afzender, afleveradres, frankeringsvoorschrift, vervoerder, goederentabel met
aantal/verpakking/inhoud/gewicht, totalen, plaats en datum van afzending).

Juridische basis: de verwijzingsclausule maakt de Algemene Vervoercondities
2002 van toepassing op het binnenlands wegvervoer. Voor gevaarlijke stoffen
geldt dat ADR 5.4.1 geen vorm voorschrijft: de vrachtbrief zelf is het
vervoersdocument zolang de omschrijving van 5.4.1.1.1 erin staat. Die wordt
hier per collo in de kolom 'inhoud' geplaatst.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.dg.autofill import adr_category_totals, description_line
from app.services.documents.exporter import _lang, _text
from app.services.documents.pdf_render import _output_path

INK = colors.HexColor("#5B4A21")
FILL = colors.HexColor("#F7F4DC")
GRID = colors.HexColor("#8A7A40")

# Vaste tekst zoals die op het formulier staat; de verwijzingsclausule maakt de
# AVC 2002 van toepassing (sVa / Stichting Vervoeradres).
CONDITIONS_NL = (
    "niet voor rembourszendingen · in de vracht is verzekering niet inbegrepen · "
    "uitsluitend voor ongeregeld vervoer — ministeriële regeling 27-12-04/HDJZ/S&amp;W2004-2842\n"
    "Het vervoer geschiedt op de door sVa / Stichting Vervoeradres ter griffie van de "
    "arrondissementsrechtbank te Amsterdam en Rotterdam gedeponeerde Algemene "
    "Vervoercondities 2002, laatste versie."
)
CONDITIONS_EN = (
    "not for cash-on-delivery consignments · insurance is not included in the freight · "
    "for irregular carriage only — ministerial regulation 27-12-04/HDJZ/S&amp;W2004-2842\n"
    "Carriage is subject to the General Transport Conditions 2002 (AVC 2002), latest version, "
    "filed by sVa / Stichting Vervoeradres with the district courts of Amsterdam and Rotterdam."
)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "banner": ParagraphStyle("avc_banner", parent=base["Normal"], fontSize=11,
                                 leading=13, textColor=colors.white, fontName="Helvetica-Bold"),
        "bannersub": ParagraphStyle("avc_bsub", parent=base["Normal"], fontSize=6.5,
                                    leading=8, textColor=colors.white),
        "label": ParagraphStyle("avc_label", parent=base["Normal"], fontSize=7,
                                leading=8.5, textColor=INK),
        "value": ParagraphStyle("avc_value", parent=base["Normal"], fontSize=8.5, leading=10.5),
        "cell": ParagraphStyle("avc_cell", parent=base["Normal"], fontSize=7.5, leading=9),
        "fine": ParagraphStyle("avc_fine", parent=base["Normal"], fontSize=5.8,
                               leading=7, textColor=INK),
        "disclaimer": ParagraphStyle("avc_disc", parent=base["Normal"], fontSize=6.5,
                                     leading=8, textColor=colors.HexColor("#666666")),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    s = "" if text is None else str(text)
    s = s.replace("&amp;", "\x00").replace("&", "&amp;").replace("\x00", "&amp;")
    s = s.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    return Paragraph(s, style)


def _box(label: str, value: Any, styles: dict, width: float, height: float) -> Table:
    """Eén vak met het veldlabel linksboven en de waarde eronder."""
    inner = [[_p(label, styles["label"])], [_p(value, styles["value"])]]
    t = Table(inner, colWidths=[width], rowHeights=[9, height - 9])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("VALIGN", (0, 0), (-1, 0), "TOP"),
        ("VALIGN", (0, 1), (-1, 1), "TOP"),
    ]))
    return t


def _banner(title: str, subtitle: str, styles: dict, width: float) -> Table:
    t = Table([[_p(title, styles["banner"])], [_p(subtitle, styles["bannersub"])]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _franking(values: dict[str, Any], styles: dict, width: float, lang: str) -> Table:
    """Frankeringsvoorschrift: Franco / Niet franco met aangekruist vakje."""
    choice = str(values.get("freight_payment") or values.get("franking") or "").strip().lower()
    franco = "X" if choice in {"franco", "prepaid", "vooruitbetaald"} else " "
    not_franco = "X" if choice in {"niet franco", "not franco", "collect", "ongefrankeerd"} else " "
    label = "frankeringsvoorschrift" if lang == "nl" else "franking instruction"
    rows = [
        [_p(label, styles["label"])],
        [_p(f"[{franco}]  Franco", styles["value"])],
        [_p(f"[{not_franco}]  " + ("Niet franco" if lang == "nl" else "Not franco"), styles["value"])],
    ]
    t = Table(rows, colWidths=[width], rowHeights=[9, 11, 11])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _goods_rows(
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
) -> tuple[list[list[str]], float, float]:
    """Rijen (aantal, verpakking, inhoud, gewicht) plus de totalen.

    Bij een collo met gevaarlijke stoffen komt de ADR 5.4.1.1.1-omschrijving in
    de kolom 'inhoud'; daarmee is de vrachtbrief tevens het vervoersdocument.
    """
    dg_by_line: dict[Any, list[str]] = {}
    for entry in dangerous_goods or []:
        for product in entry.get("products") or []:
            if str(product.get("un_number") or "").strip():
                dg_by_line.setdefault(entry.get("line_id"), []).append(
                    description_line(product, "ADR")
                )

    rows: list[list[str]] = []
    total_count = 0.0
    total_weight = 0.0
    for line in lines:
        if not line.get("include", True):
            continue
        quantity = line.get("quantity")
        weight = line.get("weight_total_kg")
        if quantity not in (None, ""):
            try:
                total_count += float(quantity)
            except (TypeError, ValueError):
                pass
        if weight not in (None, ""):
            try:
                total_weight += float(weight)
            except (TypeError, ValueError):
                pass
        contents = dg_by_line.get(line.get("line_id"))
        description = (
            "\n".join(contents)
            if contents
            else (line.get("output_description") or line.get("description") or "")
        )
        rows.append([
            "" if quantity in (None, "") else str(quantity),
            str(line.get("unit") or ""),
            description,
            "" if weight in (None, "") else str(weight),
        ])
    return rows, total_count, total_weight


def _goods_table(rows: list[list[str]], styles: dict, width: float, lang: str) -> Table:
    header = (
        ["aantal", "verpakking", "inhoud", "gewicht in kg"]
        if lang == "nl"
        else ["number", "packaging", "contents", "weight in kg"]
    )
    widths = [width * 0.12, width * 0.20, width * 0.52, width * 0.16]
    data = [[_p(h, styles["label"]) for h in header]]
    for row in rows:
        data.append([_p(cell, styles["cell"]) for cell in row])
    # Minimaal enkele lege regels zodat het formulier zijn vorm houdt.
    for _ in range(max(0, 6 - len(rows))):
        data.append([_p("", styles["cell"]) for _ in header])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, INK),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, GRID),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 1), (0, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _pair(left: Table, right: Table, width: float, ratio: float = 0.5) -> Table:
    t = Table([[left, right]], colWidths=[width * ratio, width * (1 - ratio)])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _party(name: Any, address: Any, contact: Any = "") -> str:
    return "\n".join(str(x).strip() for x in (name, address, contact) if str(x or "").strip())


def render_avc_waybill(
    document: dict[str, Any],
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
    signature_png: bytes | None = None,
) -> Path:
    lang = _lang(language)
    styles = _styles()
    out_path = _output_path()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        title="AVC-vrachtbrief" if lang == "nl" else "AVC waybill",
    )
    width = doc.width
    left_w = width * 0.62 - 3 * mm
    right_w = width * 0.38 - 3 * mm
    story: list = []

    # ── Koppen ──────────────────────────────────────────────────────────────
    story.append(_pair(
        _banner(
            "VRACHTBRIEF — VERVOERDOCUMENT" if lang == "nl" else "WAYBILL — TRANSPORT DOCUMENT",
            "exemplaar voor afzender" if lang == "nl" else "copy for consignor",
            styles, left_w),
        _banner(
            "ONTVANGSTBEWIJS" if lang == "nl" else "RECEIPT",
            "exemplaar voor afzender" if lang == "nl" else "copy for consignor",
            styles, right_w),
        width, 0.62))
    story.append(Spacer(1, 2))

    # ── Afzender + voorwaardenblok ──────────────────────────────────────────
    consignor = _party(values.get("consignor_name"), values.get("consignor_address"),
                       values.get("consignor_contact"))
    conditions = Table(
        [[_p(CONDITIONS_NL if lang == "nl" else CONDITIONS_EN, styles["fine"])]],
        colWidths=[left_w * 0.42], rowHeights=[34 * mm])
    conditions.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(_pair(
        _pair(_box("afzender" if lang == "nl" else "consignor", consignor, styles,
                   left_w * 0.58, 34 * mm), conditions, left_w, 0.58),
        _box("afzender" if lang == "nl" else "consignor", consignor, styles, right_w, 34 * mm),
        width, 0.62))

    # ── Afleveradres ────────────────────────────────────────────────────────
    delivery = _party(values.get("consignee_name"), values.get("consignee_address"),
                      values.get("place_of_delivery"))
    label_delivery = "afleveradres" if lang == "nl" else "delivery address"
    story.append(_pair(
        _box(label_delivery, delivery, styles, left_w, 30 * mm),
        _box(label_delivery, delivery, styles, right_w, 30 * mm),
        width, 0.62))

    # ── Frankeringsvoorschrift + vervoerder ─────────────────────────────────
    carrier = _party(values.get("carrier_name"), values.get("carrier_address"))
    label_carrier = "vervoerder" if lang == "nl" else "carrier"
    story.append(_pair(
        _pair(_franking(values, styles, left_w * 0.3, lang),
              _box(label_carrier, carrier, styles, left_w * 0.7, 31), left_w, 0.3),
        _pair(_franking(values, styles, right_w * 0.42, lang),
              _box(label_carrier, carrier, styles, right_w * 0.58, 31), right_w, 0.42),
        width, 0.62))

    # ── Goederen + ontvangstblok ────────────────────────────────────────────
    rows, total_count, total_weight = _goods_rows(lines, dangerous_goods)
    receipt = _box(
        "handtekening en kenteken vervoerder" if lang == "nl"
        else "signature and registration of carrier",
        values.get("vehicle_registration") or "", styles, right_w, 48 * mm)
    story.append(_pair(_goods_table(rows, styles, left_w, lang), receipt, width, 0.62))

    # ── Totalen ─────────────────────────────────────────────────────────────
    totals_text = (
        f"totaal aantal: {int(total_count) if total_count.is_integer() else total_count}"
        f"          gewicht: {round(total_weight, 2)} kg"
        if lang == "nl" else
        f"total number: {int(total_count) if total_count.is_integer() else total_count}"
        f"          weight: {round(total_weight, 2)} kg"
    )
    story.append(_pair(
        _box("totaal" if lang == "nl" else "total", totals_text, styles, left_w, 24),
        _box("totaal aantal / gewicht" if lang == "nl" else "total number / weight",
             totals_text, styles, right_w, 24),
        width, 0.62))

    # ── Plaats en datum van afzending ───────────────────────────────────────
    place_date = "        ".join(x for x in [
        str(values.get("loading_point") or values.get("place_of_receipt") or ""),
        str(values.get("loading_date") or values.get("established_date") or ""),
    ] if x)
    story.append(_pair(
        _box("plaats van afzending / datum" if lang == "nl" else "place of dispatch / date",
             place_date, styles, left_w, 22),
        _box("datum" if lang == "nl" else "date",
             str(values.get("loading_date") or ""), styles, right_w, 22),
        width, 0.62))

    # ── Gevaarlijke stoffen: totaal per vervoerscategorie ───────────────────
    if dangerous_goods:
        totals = adr_category_totals(dangerous_goods, lang)
        if totals["statement"]:
            story.append(Spacer(1, 3))
            story.append(_p(totals["statement"], styles["cell"]))

    # ── Handtekening afzender ───────────────────────────────────────────────
    if signature_png:
        story.append(Spacer(1, 4))
        try:
            image = Image(__import__("io").BytesIO(signature_png))
            ratio = image.imageHeight / max(image.imageWidth, 1)
            image.drawWidth = 45 * mm
            image.drawHeight = min(45 * mm * ratio, 18 * mm)
            block = [
                _p("handtekening afzender" if lang == "nl" else "signature of consignor",
                   styles["label"]),
                image,
            ]
            story.append(KeepTogether(block))
        except Exception:  # pragma: no cover - beschadigde afbeelding
            pass

    story.append(Spacer(1, 4))
    story.append(_p(_text("disclaimer", lang), styles["disclaimer"]))

    doc.build(story)
    return out_path
