import json
import re
from dataclasses import dataclass, field
from typing import Any


DESCRIPTION_ALIASES = {
    "description", "artikelomschrijving", "artikelnaam", "omschrijving",
    "material description", "specifications", "item", "product",
}
QUANTITY_ALIASES = {"quantity", "aantal", "qty", "count", "amount"}
UNIT_ALIASES = {"unit", "eenheid", "units", "stuks", "pcs"}


@dataclass
class ParsedRow:
    raw: str
    description: str = ""
    quantity: float | None = None
    unit: str | None = None
    columns: dict[str, str] = field(default_factory=dict)


def split_paste(text: str) -> list[list[str]]:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    rows: list[list[str]] = []
    for line in lines:
        if "\t" in line:
            rows.append([c.strip() for c in line.split("\t")])
        elif "|" in line:
            rows.append([c.strip() for c in line.split("|")])
        elif ";" in line and line.count(";") >= 2:
            rows.append([c.strip() for c in line.split(";")])
        else:
            match = re.match(r"^(.+?)\s+(\d+(?:[.,]\d+)?)\s+(\w+)?\s*$", line)
            if match:
                rows.append([match.group(1).strip(), match.group(2), (match.group(3) or "").strip()])
            else:
                rows.append([line])
    return rows


def detect_columns(header: list[str]) -> dict[str, int | None]:
    mapping: dict[str, int | None] = {"description": None, "quantity": None, "unit": None}
    lowered = [h.lower().strip() for h in header]
    for idx, col in enumerate(lowered):
        if col in DESCRIPTION_ALIASES:
            mapping["description"] = idx
        elif col in QUANTITY_ALIASES:
            mapping["quantity"] = idx
        elif col in UNIT_ALIASES:
            mapping["unit"] = idx
    return mapping


def infer_columns(rows: list[list[str]], has_header: bool = False) -> dict[str, int | None]:
    if not rows:
        return {"description": 0, "quantity": None, "unit": None}
    if has_header:
        header_map = detect_columns(rows[0])
        if header_map["description"] is not None or header_map["quantity"] is not None:
            return header_map
    first = rows[0]
    mapping: dict[str, int | None] = {"description": 0, "quantity": None, "unit": None}
    if len(first) >= 2:
        mapping["quantity"] = 1
    if len(first) >= 3:
        mapping["unit"] = 2
    return mapping


def _parse_quantity(value: str) -> float | None:
    value = value.strip().replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def parse_paste(
    text: str,
    column_map: dict[str, int | None] | None = None,
    has_header: bool = False,
) -> tuple[list[ParsedRow], dict[str, int | None]]:
    rows = split_paste(text)
    if not rows:
        return [], {"description": 0, "quantity": None, "unit": None}
    mapping = column_map or infer_columns(rows, has_header=has_header)
    start = 1 if has_header else 0
    parsed: list[ParsedRow] = []
    for row in rows[start:]:
        desc_idx = mapping.get("description", 0) or 0
        qty_idx = mapping.get("quantity")
        unit_idx = mapping.get("unit")
        description = row[desc_idx] if desc_idx < len(row) else (row[0] if row else "")
        quantity = None
        unit = None
        if qty_idx is not None and qty_idx < len(row):
            quantity = _parse_quantity(row[qty_idx])
        if unit_idx is not None and unit_idx < len(row):
            unit = row[unit_idx] or None
        parsed.append(
            ParsedRow(
                raw="\t".join(row),
                description=description,
                quantity=quantity,
                unit=unit,
                columns={str(i): v for i, v in enumerate(row)},
            )
        )
    return parsed, mapping
