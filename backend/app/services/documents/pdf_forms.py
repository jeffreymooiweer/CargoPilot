"""Vul officiële, invulbare PDF-formulieren (AcroForm) in met CargoPilot-gegevens.

De templates staan als echte, door de uitgevende instantie gepubliceerde
PDF-formulieren in ``templates/forms/`` en worden ingevuld — niet nagebouwd.
Handtekening-, carrier- en operationele velden blijven bewust leeg.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject

from app.core.config import get_settings

# IATA open-formaat: elk van de twee keuzeparen bestaat uit twee /Ch-velden. Het
# doorgehaalde (niet-toepasselijke) veld krijgt de "XXX"-optie, het toepasselijke
# veld de lege optie. De template pre-fillt deze velden, dus beide worden altijd
# expliciet gezet zodat de standaardwaarde niet doorlekt.
_IATA_AIRCRAFT_STRIKE = "XXX"
_IATA_AIRCRAFT_BLANK = " " * 11
_IATA_SHIPTYPE_STRIKE = "XXXXXXXXXXX"
_IATA_SHIPTYPE_BLANK = " " * 12

CMR_MAX_ROWS = 16


def templates_forms_dir() -> Path:
    settings = get_settings()
    candidates = [
        settings.data_dir / "templates" / "forms",
        Path(__file__).resolve().parents[3] / ".." / "templates" / "forms",
    ]
    for path in candidates:
        resolved = path.resolve()
        if resolved.exists():
            return resolved
    # Val terug op de repo-bundel zodat dev zonder /data ook werkt.
    return (Path(__file__).resolve().parents[3] / ".." / "templates" / "forms").resolve()


def _party(name: str, address: str, contact: str = "") -> str:
    parts = [p.strip() for p in (name, address, contact) if p and p.strip()]
    return "\n".join(parts)


def _first(*values: Any) -> str:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return ""


def _freight_payment_label(value: str, lang: str) -> str:
    labels = {
        "prepaid": {"nl": "Franco", "en": "Carriage paid"},
        "collect": {"nl": "Ongefrankeerd", "en": "Carriage forward"},
        "agreement": {"nl": "Volgens overeenkomst", "en": "As per agreement"},
    }
    return labels.get(value, {}).get(lang, value or "")


def _cmr_goods_rows(lines: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in lines:
        if not line.get("include", True):
            continue
        qty = line.get("quantity")
        desc = line.get("output_description") or line.get("description") or ""
        prefix = f"{qty} × " if qty not in (None, "") else ""
        weight = line.get("weight_total_kg")
        volume = line.get("transport_volume_m3")
        rows.append(
            (
                f"{prefix}{desc}".strip(),
                "" if weight in (None, "") else str(weight),
                "" if volume in (None, "") else str(volume),
            )
        )
    return rows


def fill_cmr(values: dict[str, Any], lines: list[dict[str, Any]], lang: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    fields["VakRood01"] = _party(
        values.get("consignor_name", ""),
        values.get("consignor_address", ""),
        values.get("consignor_contact", ""),
    )
    fields["VakRood02"] = _party(
        values.get("consignee_name", ""),
        values.get("consignee_address", ""),
        values.get("consignee_contact", ""),
    )
    fields["VakRood03"] = _first(values.get("place_of_delivery"), values.get("discharge_point"))
    fields["VakRood04-1"] = _first(values.get("loading_point"), values.get("place_of_receipt"))
    if values.get("loading_date"):
        fields["VeldRood04-2"] = str(values["loading_date"])
    fields["VakRood05"] = _first(values.get("attached_documents"))
    fields["VakRood13"] = _first(values.get("sender_instructions"))
    fields["VakRood14"] = _freight_payment_label(str(values.get("freight_payment", "")), lang)
    fields["VakRood15"] = _first(values.get("cod_amount"))
    fields["VakRood16"] = _first(values.get("carrier_name"))
    fields["VakRood17"] = _first(values.get("successive_carriers"))
    fields["VakRood19"] = _first(values.get("special_agreements"))
    fields["VakRood21-1"] = _first(values.get("established_place"))
    fields["VakRood21-2"] = _first(values.get("established_date"))

    rows = _cmr_goods_rows(lines)
    if len(rows) <= CMR_MAX_ROWS:
        for i, (desc, weight, volume) in enumerate(rows, start=1):
            n = f"{i:02d}"
            fields[f"VakRood06Regel{n}Kolom06"] = desc
            fields[f"VakRood06Regel{n}Kolom11"] = weight
            fields[f"VakRood06Regel{n}Kolom12"] = volume
    else:
        # Meer regels dan het formulier aankan: eerste regels + verwijzing naar bijlage.
        for i in range(1, CMR_MAX_ROWS):
            desc, weight, volume = rows[i - 1]
            n = f"{i:02d}"
            fields[f"VakRood06Regel{n}Kolom06"] = desc
            fields[f"VakRood06Regel{n}Kolom11"] = weight
            fields[f"VakRood06Regel{n}Kolom12"] = volume
        total_weight = sum(float(w) for _, w, _ in rows if w)
        total_volume = sum(float(v) for _, _, v in rows if v)
        n = f"{CMR_MAX_ROWS:02d}"
        note = "zie bijgevoegde paklijst" if lang == "nl" else "see attached packing list"
        fields[f"VakRood06Regel{n}Kolom06"] = f"+{len(rows) - (CMR_MAX_ROWS - 1)} regels — {note}"
        fields[f"VakRood06Regel{n}Kolom11"] = str(round(total_weight, 2))
        fields[f"VakRood06Regel{n}Kolom12"] = str(round(total_volume, 3))
    return {k: v for k, v in fields.items() if v not in (None, "")}


def _iata_dg_block(dangerous_goods: list[dict[str, Any]]) -> str:
    """Regels voor het 'Nature and Quantity of Dangerous Goods'-veld, IATA-kolomvolgorde."""
    out: list[str] = []
    for entry in dangerous_goods or []:
        for p in entry.get("products", []):
            un = str(p.get("un_number") or "").strip()
            un = un if un.upper().startswith(("UN", "ID")) else (f"UN {un}" if un else "")
            psn = str(p.get("proper_shipping_name") or "").strip()
            technical = str(p.get("technical_name") or "").strip()
            if technical:
                psn = f"{psn} ({technical})"
            hazard = str(p.get("class") or "").strip()
            subsidiary = str(p.get("subsidiary_risks") or "").strip()
            if subsidiary:
                hazard = f"{hazard} ({subsidiary})"
            pg = str(p.get("packing_group") or "").strip()
            qty_parts = [
                str(p.get("quantity_packages") or "").strip(),
                str(p.get("type_of_package") or "").strip(),
            ]
            qty = " x ".join(x for x in qty_parts if x)
            per = str(p.get("net_mass_liters_per_package") or "").strip()
            if per:
                qty = f"{qty}, {per}" if qty else per
            pi = str(p.get("packing_instruction") or "").strip()
            segments = [s for s in [un, psn, hazard, pg, qty, pi] if s]
            if segments:
                out.append("   ".join(segments))
    return "\n".join(out)


def fill_iata(values: dict[str, Any], dangerous_goods: list[dict[str, Any]], lang: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    fields["Shipper"] = _party(
        values.get("consignor_name", ""),
        values.get("consignor_address", ""),
        values.get("consignor_contact", ""),
    )
    fields["Consignee"] = _party(
        values.get("consignee_name", ""),
        values.get("consignee_address", ""),
        values.get("consignee_contact", ""),
    )
    if values.get("awb_number"):
        fields["Air Waybill No"] = str(values["awb_number"])
    if values.get("shipment_reference"):
        fields["Shipper Reference"] = str(values["shipment_reference"])
    fields["Departure Airport"] = _first(values.get("loading_point"))
    fields["Destination Airport"] = _first(values.get("discharge_point"))
    fields["Additional Handling Information"] = _first(values.get("handling_information"))
    fields["Nature and Quantity of Dangerous Goods"] = _iata_dg_block(dangerous_goods)

    # "Delete non-applicable": streep de NIET-toepasselijke optie door en zet het
    # toepasselijke veld expliciet leeg (anders lekt de template-standaard door).
    aircraft = str(values.get("aircraft_limitation") or "")
    if aircraft == "cargo_only":
        fields["Passenger and Cargo Aircraft"] = _IATA_AIRCRAFT_STRIKE
        fields["Cargo Aircraft Only"] = _IATA_AIRCRAFT_BLANK
    elif aircraft == "passenger_and_cargo":
        fields["Cargo Aircraft Only"] = _IATA_AIRCRAFT_STRIKE
        fields["Passenger and Cargo Aircraft"] = _IATA_AIRCRAFT_BLANK

    ship_type = str(values.get("shipment_type") or "")
    if ship_type == "non_radioactive":
        fields["radioactive ship type"] = _IATA_SHIPTYPE_STRIKE
        fields["non-rad ship type"] = _IATA_SHIPTYPE_BLANK
    elif ship_type == "radioactive":
        fields["non-rad ship type"] = _IATA_SHIPTYPE_STRIKE
        fields["radioactive ship type"] = _IATA_SHIPTYPE_BLANK

    signatory = _first(values.get("signatory_name"))
    if signatory:
        fields["Name-title"] = signatory
    place_date = " / ".join(
        x for x in [_first(values.get("declaration_place")), _first(values.get("declaration_date"))] if x
    )
    if place_date:
        fields["place-date"] = place_date
    return {k: v for k, v in fields.items() if v not in (None, "")}


# Per document: welke template en welke veld-builder.
PDF_FILLERS: dict[str, tuple[str, Callable[..., dict[str, str]]]] = {
    "cmr": ("cmr.pdf", "cmr"),
    "iata_dgd": ("iata_dgd.pdf", "iata"),
}


def build_fields(
    document_key: str,
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    lang: str,
) -> dict[str, str]:
    if document_key == "cmr":
        return fill_cmr(values, lines, lang)
    if document_key == "iata_dgd":
        return fill_iata(values, dangerous_goods or [], lang)
    raise ValueError(f"No PDF filler for {document_key}")


def has_pdf_template(document_key: str) -> bool:
    if document_key not in PDF_FILLERS:
        return False
    template = PDF_FILLERS[document_key][0]
    return (templates_forms_dir() / template).exists()


def fill_pdf_document(
    document_key: str,
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    lang: str = "nl",
) -> Path:
    if document_key not in PDF_FILLERS:
        raise ValueError(f"No PDF template for {document_key}")
    template_name = PDF_FILLERS[document_key][0]
    template_path = templates_forms_dir() / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"PDF template not found: {template_path}")

    fields = build_fields(document_key, values, lines, dangerous_goods, lang)

    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.append(reader)

    for page in writer.pages:
        writer.update_page_form_field_values(page, fields, auto_regenerate=False)

    disclaimer = (
        "CONCEPT — gegenereerd met CargoPilot. Controleer, vul aan en onderteken door een "
        "bevoegde persoon voor gebruik. Geen aansprakelijkheid; geleverd AS IS onder de "
        "Apache License 2.0 met Commons Clause. Zie DISCLAIMER.md. / DRAFT — generated with "
        "CargoPilot; verify, complete and sign before use. No liability; provided AS IS."
    )
    try:
        writer.add_metadata(
            {
                "/Producer": "CargoPilot",
                "/Creator": "CargoPilot",
                "/Subject": disclaimer,
            }
        )
    except Exception:
        pass

    # Zorg dat viewers de ingevulde waarden renderen.
    try:
        writer.set_need_appearances_writer(True)
    except Exception:
        root = writer._root_object
        if "/AcroForm" in root:
            root["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)

    fd, temp_name = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    out_path = Path(temp_name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    with open(out_path, "wb") as fh:
        writer.write(fh)
    return out_path
