"""Bulk-import van materieel uit spreadsheet."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.user import Equipment
from app.services.spreadsheet_io import normalize_header

EQUIPMENT_HEADERS = [
    "sap_code",
    "specifications",
    "length_cm",
    "width_cm",
    "height_cm",
    "weight_kg",
    "aliases",
    "active",
]

EQUIPMENT_EXAMPLE = [
    "DEMO-001",
    "DEMO LIGHT VEHICLE",
    "400",
    "180",
    "170",
    "1200",
    "demo vehicle, demo light vehicle",
    "yes",
]

COLUMN_ALIASES: dict[str, set[str]] = {
    "sap_code": {"sap_code", "sap", "matnr", "material", "code"},
    "specifications": {"specifications", "specification", "specs", "omschrijving", "description", "naam"},
    "length_cm": {"length_cm", "length", "lengte", "l"},
    "width_cm": {"width_cm", "width", "breedte", "b"},
    "height_cm": {"height_cm", "height", "hoogte", "h"},
    "weight_kg": {"weight_kg", "weight", "gewicht", "kg"},
    "aliases": {"aliases", "alias", "synoniemen", "synonyms"},
    "active": {"active", "actief", "enabled"},
}


@dataclass
class EquipmentImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _detect_column_map(header: list[str]) -> dict[str, int | None]:
    mapping = {key: None for key in EQUIPMENT_HEADERS}
    for idx, col in enumerate(header):
        norm = normalize_header(col)
        for field_name, aliases in COLUMN_ALIASES.items():
            if norm in aliases:
                mapping[field_name] = idx
    return mapping


def _infer_column_map(row: list[str]) -> dict[str, int | None]:
    if len(row) >= 8:
        return {key: idx for idx, key in enumerate(EQUIPMENT_HEADERS)}
    mapping: dict[str, int | None] = {key: None for key in EQUIPMENT_HEADERS}
    mapping["specifications"] = 0
    if len(row) >= 2:
        mapping["weight_kg"] = 1
    if len(row) >= 3:
        mapping["length_cm"] = 2
    if len(row) >= 4:
        mapping["width_cm"] = 3
    if len(row) >= 5:
        mapping["height_cm"] = 4
    return mapping


def _has_header_row(rows: list[list[str]]) -> bool:
    if not rows:
        return False
    header_map = _detect_column_map(rows[0])
    return header_map["specifications"] is not None or header_map["weight_kg"] is not None


def _parse_float(value: str) -> float | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_bool(value: str) -> bool:
    norm = value.strip().lower()
    if norm in {"", "yes", "y", "ja", "j", "true", "1", "actief", "active"}:
        return True
    if norm in {"no", "n", "nee", "false", "0", "inactief", "inactive"}:
        return False
    return True


def _parse_aliases(value: str) -> list[str]:
    if not value.strip():
        return []
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


def _row_to_record(row: list[str], mapping: dict[str, int | None]) -> dict:
    def cell(field: str) -> str:
        idx = mapping.get(field)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    return {
        "sap_code": cell("sap_code") or None,
        "specifications": cell("specifications"),
        "length_cm": _parse_float(cell("length_cm")),
        "width_cm": _parse_float(cell("width_cm")),
        "height_cm": _parse_float(cell("height_cm")),
        "weight_kg": _parse_float(cell("weight_kg")),
        "aliases": _parse_aliases(cell("aliases")),
        "active": _parse_bool(cell("active")) if cell("active") else True,
    }


def import_equipment_rows(db: Session, rows: list[list[str]]) -> EquipmentImportResult:
    result = EquipmentImportResult()
    if not rows:
        result.errors.append("Geen rijen gevonden in het bestand.")
        return result

    has_header = _has_header_row(rows)
    mapping = _detect_column_map(rows[0]) if has_header else _infer_column_map(rows[0])
    if has_header and mapping["specifications"] is None:
        mapping["specifications"] = 1 if mapping["sap_code"] == 0 else 0

    start = 1 if has_header else 0
    for line_no, row in enumerate(rows[start:], start=start + 1):
        record = _row_to_record(row, mapping)
        specs = record["specifications"]
        weight = record["weight_kg"]
        if not specs:
            result.skipped += 1
            continue
        if weight is None or weight <= 0:
            result.errors.append(f"Regel {line_no}: gewicht ontbreekt of is ongeldig.")
            result.skipped += 1
            continue

        existing = None
        if record["sap_code"]:
            existing = db.query(Equipment).filter(Equipment.sap_code == record["sap_code"]).first()
        if existing is None:
            existing = (
                db.query(Equipment)
                .filter(Equipment.specifications.ilike(specs))
                .first()
            )

        if existing:
            existing.sap_code = record["sap_code"] or existing.sap_code
            existing.specifications = specs
            existing.length_cm = record["length_cm"]
            existing.width_cm = record["width_cm"]
            existing.height_cm = record["height_cm"]
            existing.weight_kg = weight
            if record["aliases"]:
                existing.aliases_json = json.dumps(record["aliases"])
            existing.active = record["active"]
            result.updated += 1
        else:
            db.add(
                Equipment(
                    sap_code=record["sap_code"],
                    specifications=specs,
                    length_cm=record["length_cm"],
                    width_cm=record["width_cm"],
                    height_cm=record["height_cm"],
                    weight_kg=weight,
                    aliases_json=json.dumps(record["aliases"]),
                    language_labels_json="{}",
                    source="import",
                    active=record["active"],
                )
            )
            result.created += 1

    db.commit()
    return result
