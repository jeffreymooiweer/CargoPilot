import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import Material, Profile, ReferenceItem
from app.services.calculator.engine import (
    STEEL_DENSITY,
    CalculationResult,
    LineStatus,
    calc_angle_profile,
    calc_catalog_profile,
    calc_hollow_rect,
    transport_volume_outer,
)
from app.services.parser.dimension_extractor import Dimensions, extract_dimensions, meters_to_cm
from app.services.parser.language_detector import detect_language
from app.services.parser.paste_parser import ParsedRow, parse_paste
from app.services.parser.product_detector import detect_product_type

PRODUCT_LABELS = {
    "angle_profile": {"nl": "Hoekprofiel", "en": "Angle profile"},
    "square_tube": {"nl": "Kokerprofiel", "en": "Square tube"},
    "round_tube": {"nl": "Buis", "en": "Pipe"},
    "round_bar": {"nl": "Ronde staf", "en": "Round bar"},
    "plate": {"nl": "Plaat", "en": "Plate"},
    "beam": {"nl": "Balk", "en": "Beam"},
    "standard_profile": {"nl": "Staalprofiel", "en": "Steel profile"},
    "concrete_slab": {"nl": "Betonplaat", "en": "Concrete slab"},
    "plywood": {"nl": "Plaatmateriaal", "en": "Sheet material"},
    "reference_item": {"nl": "Artikel", "en": "Item"},
    "unknown": {"nl": "Onbekend", "en": "Unknown"},
}


@dataclass
class LineResult:
    line_id: int
    raw: str
    description: str
    output_description: str
    quantity: float | None
    unit: str | None
    material: str | None = None
    material_density: float | None = None
    product_type: str | None = None
    dimensions: dict[str, Any] = field(default_factory=dict)
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    weight_each_kg: float | None = None
    weight_total_kg: float | None = None
    material_volume_m3: float | None = None
    transport_volume_m3: float | None = None
    kg_per_meter: float | None = None
    status: str = "ok"
    messages: list[str] = field(default_factory=list)
    confidence: float = 1.0
    include: bool = True
    input_language: str = "nl"
    calculation_method: str | None = None


def _load_aliases_json(raw: str) -> list[str]:
    try:
        return json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []


def match_material(text: str, db: Session) -> tuple[Material | None, float]:
    lower = text.lower()
    best: Material | None = None
    best_len = 0
    for material in db.query(Material).filter(Material.active.is_(True)).all():
        aliases = [material.canonical_name.lower(), *_load_aliases_json(material.aliases_json)]
        labels = json.loads(material.language_labels_json or "{}")
        aliases.extend(v.lower() for v in labels.values())
        for alias in aliases:
            if alias and alias in lower and len(alias) > best_len:
                best = material
                best_len = len(alias)
    return best, best.density_kg_m3 if best else STEEL_DENSITY


def match_profile(text: str, dims: Dimensions, db: Session) -> Profile | None:
    candidates = []
    if dims.profile_size:
        candidates.append(dims.profile_size.lower())
    for profile in db.query(Profile).filter(Profile.active.is_(True)).all():
        aliases = [f"{profile.profile_type} {profile.size_label}".lower(), profile.size_label.lower()]
        aliases.extend(a.lower() for a in _load_aliases_json(profile.aliases_json))
        hay = text.lower()
        for alias in aliases:
            if alias and alias in hay:
                return profile
    return None


def match_reference(text: str, db: Session) -> ReferenceItem | None:
    lower = text.lower()
    best: ReferenceItem | None = None
    best_len = 0
    for item in db.query(ReferenceItem).filter(ReferenceItem.active.is_(True)).all():
        aliases = [item.canonical_name.lower(), *_load_aliases_json(item.aliases_json)]
        for alias in aliases:
            if alias and alias in lower and len(alias) > best_len:
                best = item
                best_len = len(alias)
    return best


def build_output_description(description: str, product_type: str | None, dims: Dimensions, lang: str) -> str:
    label = PRODUCT_LABELS.get(product_type or "unknown", PRODUCT_LABELS["unknown"])[lang]
    if dims.profile_size:
        size = dims.profile_size
        length_mm = int(round((dims.length_m or 0) * 1000))
        return f"{label} {size} {length_mm} mm"
    if dims.values_m:
        mm = "x".join(str(int(round(v * 1000))) for v in dims.values_m)
        return f"{label} {mm} mm"
    return description


def process_line(
    line_id: int,
    row: ParsedRow,
    db: Session,
    input_language: str | None = None,
    output_language: str = "nl",
    overrides: dict[str, Any] | None = None,
) -> LineResult:
    overrides = overrides or {}
    lang = input_language or detect_language(row.description)
    dims = extract_dimensions(row.description)
    product_type = overrides.get("product_type") or detect_product_type(row.description)
    material_obj, density = match_material(row.description, db)
    if overrides.get("material_density"):
        density = float(overrides["material_density"])
    material_name = overrides.get("material") or (material_obj.canonical_name if material_obj else None)
    qty = overrides.get("quantity", row.quantity)
    messages: list[str] = []
    status = "ok"
    weight_each = None
    weight_total = None
    material_vol = None
    transport_vol = None
    kg_per_m = overrides.get("kg_per_meter")
    method = None
    length_cm = meters_to_cm(overrides.get("length_m") or dims.length_m)
    width_cm = meters_to_cm(overrides.get("width_m") or dims.width_m)
    height_cm = meters_to_cm(overrides.get("height_m") or dims.height_m)

    ref = match_reference(row.description, db)
    if ref and not product_type:
        product_type = "reference_item"
        weight_each = ref.reference_weight_kg
        if qty:
            weight_total = weight_each * qty
        method = "reference_weight"

    profile = match_profile(row.description, dims, db)
    if profile and not kg_per_m:
        kg_per_m = profile.kg_per_meter

    if product_type == "standard_profile" or dims.profile_size:
        product_type = "standard_profile"
        if not dims.length_m:
            messages.append("length_missing")
            status = "error"
        elif not kg_per_m:
            messages.append("kg_per_meter_missing")
            status = "needs_review"
        else:
            _, weight_total = calc_catalog_profile(kg_per_m, dims.length_m, qty or 1)
            weight_each = kg_per_m * dims.length_m
            method = "catalog_profile"
            outer_w = 0.22
            outer_h = 0.08
            transport_vol = transport_volume_outer(outer_w, outer_h, dims.length_m, qty or 1)
            length_cm = meters_to_cm(dims.length_m)
            width_cm = meters_to_cm(outer_w)
            height_cm = meters_to_cm(outer_h)

    elif product_type == "angle_profile" and len(dims.values_m) >= 4:
        leg_a, leg_b, thick, length_m = dims.values_m[:4]
        try:
            material_vol, weight_each = calc_angle_profile(leg_a, leg_b, thick, length_m, density)
            if qty:
                weight_total = weight_each * qty
            transport_vol = transport_volume_outer(leg_a, leg_b, length_m, qty or 1)
            length_cm = meters_to_cm(length_m)
            width_cm = meters_to_cm(leg_a)
            height_cm = meters_to_cm(leg_b)
            method = "angle_profile"
        except ValueError as exc:
            messages.append(str(exc))
            status = "error"

    elif product_type == "square_tube" and len(dims.values_m) >= 4:
        outer_w, outer_h, wall, length_m = dims.values_m[:4]
        try:
            material_vol, weight_each = calc_hollow_rect(outer_w, outer_h, wall, length_m, density)
            if qty:
                weight_total = weight_each * qty
            transport_vol = transport_volume_outer(outer_w, outer_h, length_m, qty or 1)
            length_cm = meters_to_cm(length_m)
            width_cm = meters_to_cm(outer_w)
            height_cm = meters_to_cm(outer_h)
            method = "hollow_rect"
        except ValueError as exc:
            messages.append("wall_thickness_invalid")
            status = "error"

    elif product_type in {"plate", "beam"} and len(dims.values_m) >= 3:
        w, h, length_m = dims.values_m[:3]
        material_vol = w * h * length_m
        weight_each = material_vol * density
        if qty:
            weight_total = weight_each * qty
        transport_vol = transport_volume_outer(w, h, length_m, qty or 1)
        length_cm = meters_to_cm(length_m)
        width_cm = meters_to_cm(w)
        height_cm = meters_to_cm(h)
        method = "solid_block"

    else:
        if not material_obj:
            messages.append("material_not_recognized")
            status = "needs_review" if status == "ok" else status
        if not qty:
            messages.append("quantity_missing")
            status = "error"
        if not dims.length_m and not weight_each:
            messages.append("dimensions_missing")
            status = "needs_review" if status == "ok" else status

    if not material_name and ("staal" in row.description.lower() or "steel" in row.description.lower()):
        material_name = "steel"
        density = STEEL_DENSITY

    output_desc = overrides.get("output_description") or build_output_description(
        row.description, product_type, dims, output_language
    )

    return LineResult(
        line_id=line_id,
        raw=row.raw,
        description=row.description,
        output_description=output_desc,
        quantity=qty,
        unit=row.unit,
        material=material_name,
        material_density=density,
        product_type=product_type,
        dimensions={
            "values_m": dims.values_m,
            "profile_size": dims.profile_size,
            "length_m": dims.length_m,
        },
        length_cm=length_cm,
        width_cm=width_cm,
        height_cm=height_cm,
        weight_each_kg=round(weight_each, 2) if weight_each is not None else None,
        weight_total_kg=round(weight_total, 2) if weight_total is not None else None,
        material_volume_m3=round(material_vol, 6) if material_vol is not None else None,
        transport_volume_m3=round(transport_vol, 6) if transport_vol is not None else None,
        kg_per_meter=kg_per_m,
        status=status,
        messages=messages,
        confidence=0.7 if status == "needs_review" else (0.4 if status == "error" else 1.0),
        include=overrides.get("include", True),
        input_language=lang,
        calculation_method=method,
    )


def parse_and_calculate(
    text: str,
    db: Session,
    column_map: dict[str, int | None] | None = None,
    has_header: bool = False,
    input_language: str | None = None,
    output_language: str = "nl",
    mode: str = "continue",
    line_overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows, mapping = parse_paste(text, column_map, has_header)
    overrides_by_id = {o.get("line_id"): o for o in (line_overrides or [])}
    lines: list[LineResult] = []
    for idx, row in enumerate(rows, start=1):
        line = process_line(
            idx, row, db, input_language, output_language, overrides_by_id.get(idx)
        )
        lines.append(line)
    if mode == "strict" and any(l.status in {"error", "needs_review"} for l in lines):
        return {
            "success": False,
            "column_map": mapping,
            "lines": [asdict(l) for l in lines],
            "totals": {},
            "errors": [l.messages for l in lines if l.messages],
        }
    included = [l for l in lines if l.include and l.weight_total_kg]
    totals = {
        "line_count": len(lines),
        "included_count": len(included),
        "total_quantity": sum(l.quantity or 0 for l in included),
        "total_weight_kg": round(sum(l.weight_total_kg or 0 for l in included), 2),
        "total_material_volume_m3": round(sum(l.material_volume_m3 or 0 for l in included), 6),
        "total_transport_volume_m3": round(sum(l.transport_volume_m3 or 0 for l in included), 6),
        "warning_count": sum(1 for l in lines if l.status in {"warning", "needs_review"}),
        "error_count": sum(1 for l in lines if l.status == "error"),
    }
    return {
        "success": True,
        "column_map": mapping,
        "lines": [asdict(l) for l in lines],
        "totals": totals,
        "errors": [],
    }
