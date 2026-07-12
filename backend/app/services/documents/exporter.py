import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.services.documents.registry import condition_met, get_document, resolve_sections

TEXTS = {
    "generated_with": {
        "nl": "Gegenereerd met CargoPilot op",
        "en": "Generated with CargoPilot on",
    },
    "status": {"nl": "Documentstatus", "en": "Document status"},
    "goods": {"nl": "Goederenregels", "en": "Cargo lines"},
    "dg_table": {"nl": "Gevaarlijke stoffen", "en": "Dangerous goods"},
    "not_prefilled": {
        "nl": "niet vooraf ingevuld — handtekening/bevestiging vereist",
        "en": "not pre-filled — signature/confirmation required",
    },
    "carrier_provided": {
        "nl": "in te vullen door vervoerder/expediteur",
        "en": "to be provided by carrier/forwarder",
    },
    "operational": {
        "nl": "in te vullen tijdens uitvoering",
        "en": "to be filled in during execution",
    },
    "confirmed": {
        "nl": "Bevestigd in CargoPilot; ondertekening op het document blijft vereist",
        "en": "Confirmed in CargoPilot; signature on the document is still required",
    },
    "not_confirmed": {
        "nl": "NIET bevestigd",
        "en": "NOT confirmed",
    },
    "totals": {"nl": "Totalen", "en": "Totals"},
    "line_headers": {
        "nl": ["Nr", "Omschrijving", "Aantal", "Eenheid", "Gewicht (kg)", "Volume (m³)", "L×B×H (cm)"],
        "en": ["No", "Description", "Qty", "Unit", "Weight (kg)", "Volume (m³)", "L×W×H (cm)"],
    },
    "dg_headers": {
        "nl": [
            "Positie",
            "UN-nummer",
            "Proper Shipping Name",
            "Technische naam",
            "Klasse",
            "Nevengevaar",
            "Verpakkingsgroep",
            "Packing instruction",
            "Aantal colli",
            "Verpakkingstype",
            "Hoeveelheid per verpakking",
            "Bruto massa per verpakking",
            "Marine pollutant",
            "Cargo Aircraft Only",
            "Aanvullende informatie",
        ],
        "en": [
            "Position",
            "UN number",
            "Proper Shipping Name",
            "Technical name",
            "Class",
            "Subsidiary risk",
            "Packing group",
            "Packing instruction",
            "Packages",
            "Package type",
            "Quantity per package",
            "Gross mass per package",
            "Marine pollutant",
            "Cargo Aircraft Only",
            "Additional information",
        ],
    },
    "dg_missing": {
        "nl": "Gevaarlijke-stoffenclassificatie onvolledig voor",
        "en": "Dangerous goods classification incomplete for",
    },
    "field_required": {
        "nl": "Verplicht veld ontbreekt",
        "en": "Required field missing",
    },
    "no_dg_lines": {
        "nl": "Dit document vereist gevaarlijke-stoffenregels, maar er zijn geen DG-posities.",
        "en": "This document requires dangerous goods lines, but no DG positions exist.",
    },
    "vgm_mismatch": {
        "nl": "VGM wijkt af van de som van de componenten (methode 2)",
        "en": "VGM differs from the sum of the components (method 2)",
    },
}

DG_PRODUCT_FIELDS = [
    "un_number",
    "proper_shipping_name",
    "technical_name",
    "class",
    "subsidiary_risks",
    "packing_group",
    "packing_instruction",
    "quantity_packages",
    "type_of_package",
    "net_mass_liters_per_package",
    "gross_mass_per_package",
    "marine_pollutant",
    "cargo_aircraft_only",
    "additional_information",
]

DG_BASE_REQUIRED = ["un_number", "proper_shipping_name", "class"]
DG_PROFILE_REQUIRED = {
    "ADR": DG_BASE_REQUIRED,
    "RID": DG_BASE_REQUIRED,
    "ADN": DG_BASE_REQUIRED,
    "IMDG": DG_BASE_REQUIRED + ["quantity_packages", "type_of_package"],
    "IATA_DGR": DG_BASE_REQUIRED
    + ["packing_instruction", "quantity_packages", "type_of_package", "net_mass_liters_per_package"],
}


def _lang(language: str) -> str:
    return "en" if str(language).lower().startswith("en") else "nl"


def _label(item: dict[str, Any], lang: str) -> str:
    label = item.get("label") or {}
    return label.get(lang) or label.get("nl") or item.get("key", "")


def _text(key: str, lang: str) -> Any:
    return TEXTS[key][lang]


def _option_label(field: dict[str, Any], value: Any, lang: str) -> Any:
    for option in field.get("options", []):
        if option.get("value") == value:
            return _label(option, lang)
    return value


def validate_document(
    document: dict[str, Any],
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
) -> tuple[list[str], list[str]]:
    """Retourneer (blokkerende fouten, waarschuwingen) voor een documentexport."""
    lang = _lang(language)
    errors: list[str] = []
    warnings: list[str] = []

    for section in resolve_sections(document):
        for field in section.get("fields", []):
            if field.get("status") != "USER_REQUIRED":
                continue
            value = values.get(field["key"])
            if value is None or str(value).strip() == "":
                errors.append(f"{_text('field_required', lang)}: {_label(field, lang)}")

    profile = document.get("dg_profile")
    if profile:
        entries = dangerous_goods or []
        if document.get("dg_only") and not entries:
            errors.append(_text("no_dg_lines", lang))
        required_fields = DG_PROFILE_REQUIRED.get(profile, DG_BASE_REQUIRED)
        for entry in entries:
            for product in entry.get("products", []):
                missing = [f for f in required_fields if not str(product.get(f) or "").strip()]
                if missing:
                    position = entry.get("vehicle") or entry.get("a1_line_id") or "?"
                    errors.append(
                        f"{_text('dg_missing', lang)} '{position}': {', '.join(missing)}"
                    )

    if document["key"] == "vgm" and str(values.get("vgm_method")) == "method2":
        components = [
            values.get("cargo_mass_kg"),
            values.get("packaging_mass_kg"),
            values.get("pallets_mass_kg"),
            values.get("securing_mass_kg"),
            values.get("container_tare_kg"),
        ]
        try:
            total = sum(float(v) for v in components if v not in (None, ""))
            vgm = float(values.get("vgm_kg") or 0)
            if vgm and abs(total - vgm) > max(0.005 * vgm, 1.0):
                warnings.append(
                    f"{_text('vgm_mismatch', lang)}: {vgm} kg ≠ {round(total, 2)} kg"
                )
        except (TypeError, ValueError):
            pass

    return errors, warnings


def _dims(line: dict[str, Any]) -> str:
    parts = [line.get("length_cm"), line.get("width_cm"), line.get("height_cm")]
    if all(p in (None, "") for p in parts):
        return ""
    return " × ".join(str(p) if p not in (None, "") else "—" for p in parts)


def export_document(
    document_key: str,
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
) -> Path:
    document = get_document(document_key)
    if document is None:
        raise ValueError(f"Unknown document: {document_key}")
    lang = _lang(language)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = document.get("short_label", {}).get(lang, document_key)[:31]

    title_font = Font(bold=True, size=15)
    section_font = Font(bold=True, size=11, color="FFFFFF")
    section_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, size=10)
    header_fill = PatternFill("solid", fgColor="D9E2EC")
    note_font = Font(italic=True, size=9, color="666666")
    status_font = Font(italic=True, size=10, color="1E3A5F")
    thin = Side(style="thin", color="B0BEC5")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")

    ws.column_dimensions["A"].width = 42
    for col in range(2, 16):
        ws.column_dimensions[get_column_letter(col)].width = 22

    row = 1
    ws.cell(row, 1, _label(document, lang)).font = title_font
    row += 1
    issue = document.get("issue_status", {}).get(lang)
    if issue:
        cell = ws.cell(row, 1, f"{_text('status', lang)}: {issue}")
        cell.font = status_font
        row += 1
    ws.cell(row, 1, f"{_text('generated_with', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}").font = note_font
    row += 2

    for section in resolve_sections(document):
        fields = section.get("fields", [])
        visible = [
            f
            for f in fields
            if f.get("status") != "CONDITIONAL"
            or not f.get("condition")
            or condition_met(f.get("condition"), values)
            or str(values.get(f["key"], "")).strip() != ""
        ]
        filled_or_relevant = [
            f
            for f in visible
            if str(values.get(f["key"], "")).strip() != ""
            or f.get("status") in {"USER_REQUIRED", "CARRIER_PROVIDED", "OPERATIONAL", "SIGNATURE_REQUIRED"}
        ]
        if not filled_or_relevant:
            continue
        cell = ws.cell(row, 1, _label(section, lang))
        cell.font = section_font
        cell.fill = section_fill
        ws.cell(row, 2).fill = section_fill
        row += 1
        for field in filled_or_relevant:
            value = values.get(field["key"], "")
            status = field.get("status")
            if field.get("type") == "select" and value not in (None, ""):
                value = _option_label(field, value, lang)
            if status == "SIGNATURE_REQUIRED":
                if field.get("type") == "checkbox":
                    value = (
                        _text("confirmed", lang)
                        if str(value).lower() in {"true", "1", "yes", "ja"}
                        else _text("not_confirmed", lang)
                    )
                else:
                    value = f"[{_text('not_prefilled', lang)}]"
            elif str(value).strip() == "":
                if status == "CARRIER_PROVIDED":
                    value = f"[{_text('carrier_provided', lang)}]"
                elif status == "OPERATIONAL":
                    value = f"[{_text('operational', lang)}]"
                else:
                    value = ""
            label_cell = ws.cell(row, 1, _label(field, lang))
            label_cell.alignment = wrap
            label_cell.border = border
            value_cell = ws.cell(row, 2, value if value != "" else None)
            value_cell.alignment = wrap
            value_cell.border = border
            if isinstance(value, str) and value.startswith("["):
                value_cell.font = note_font
            row += 1
        row += 1

    included = [ln for ln in lines if ln.get("include", True)]
    if included:
        cell = ws.cell(row, 1, _text("goods", lang))
        cell.font = section_font
        cell.fill = section_fill
        row += 1
        headers = _text("line_headers", lang)
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row, col, header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
        row += 1
        total_weight = 0.0
        total_volume = 0.0
        for i, line in enumerate(included, start=1):
            weight = line.get("weight_total_kg")
            volume = line.get("transport_volume_m3")
            total_weight += weight or 0
            total_volume += volume or 0
            cells = [
                i,
                line.get("output_description") or line.get("description"),
                line.get("quantity"),
                line.get("unit"),
                weight,
                volume,
                _dims(line),
            ]
            for col, value in enumerate(cells, start=1):
                cell = ws.cell(row, col, value)
                cell.border = border
                if col == 2:
                    cell.alignment = wrap
            row += 1
        cell = ws.cell(row, 1, _text("totals", lang))
        cell.font = header_font
        ws.cell(row, 5, round(total_weight, 2)).font = header_font
        ws.cell(row, 6, round(total_volume, 3)).font = header_font
        row += 2

    if document.get("dg_profile") and dangerous_goods:
        cell = ws.cell(row, 1, f"{_text('dg_table', lang)} ({document['dg_profile']})")
        cell.font = section_font
        cell.fill = section_fill
        row += 1
        headers = _text("dg_headers", lang)
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row, col, header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
        row += 1
        for entry in dangerous_goods:
            for product in entry.get("products", []):
                cells = [entry.get("vehicle") or entry.get("a1_line_id")] + [
                    product.get(field, "") for field in DG_PRODUCT_FIELDS
                ]
                for col, value in enumerate(cells, start=1):
                    cell = ws.cell(row, col, value)
                    cell.border = border
                row += 1
        row += 1

    note = document.get("signature_note", {}).get(lang)
    if note:
        cell = ws.cell(row, 1, note)
        cell.font = note_font
        cell.alignment = wrap
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)

    fd, temp_name = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    out_path = Path(temp_name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    wb.save(out_path)
    return out_path
