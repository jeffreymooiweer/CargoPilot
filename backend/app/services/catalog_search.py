import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import Equipment, Material, Profile, ReferenceItem
from app.services.parser.dimension_extractor import extract_dimensions
from app.services.parser.product_detector import detect_product_type

_SYNONYMS_PATH = Path(__file__).resolve().parents[1] / "config" / "search_synonyms.json"

PRODUCT_LABELS_NL = {
    "angle_profile": "hoekprofiel",
    "square_tube": "kokerprofiel",
    "round_tube": "buis",
    "round_bar": "ronde staf",
    "plate": "plaat",
    "beam": "balk",
    "standard_profile": "staalprofiel",
    "concrete_slab": "betonplaat",
    "plywood": "multiplex",
    "pvc_pipe": "pvc buis",
    "plastic_sheet": "kunststof plaat",
}

MATERIAL_NL = {
    "steel": "staal",
    "stainless_steel": "rvs",
    "aluminium": "aluminium",
    "copper": "koper",
    "brass": "messing",
    "concrete": "beton",
    "reinforced_concrete": "gewapend beton",
    "spruce": "hout",
    "hardwood": "hardhout",
    "plywood": "multiplex",
    "pvc": "pvc",
    "pe": "pe",
    "pp": "pp",
    "pom": "pom",
    "nylon": "nylon",
    "acrylic": "plexiglas",
    "sand": "zand",
    "gravel": "grind",
}


@dataclass
class SearchHit:
    id: str
    source: str
    label: str
    sublabel: str | None
    value: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "label": self.label,
            "sublabel": self.sublabel,
            "value": self.value,
            "score": round(self.score, 2),
        }


def _load_aliases(raw: str) -> list[str]:
    try:
        return json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []


def _flatten_synonym_sections(data: dict[str, Any]) -> dict[str, str]:
    """Maak één map van geneste secties (products, materials, …) of platte legacy-json."""
    if not data:
        return {}
    if any(isinstance(v, dict) for v in data.values()):
        flat: dict[str, str] = {}
        for section in data.values():
            if isinstance(section, dict):
                for src, dst in section.items():
                    flat[src.lower()] = dst
        return flat
    return {str(k).lower(): str(v) for k, v in data.items()}


def _load_static_synonyms() -> dict[str, str]:
    if not _SYNONYMS_PATH.exists():
        return {}
    data = json.loads(_SYNONYMS_PATH.read_text(encoding="utf-8"))
    return _flatten_synonym_sections(data)


def _db_synonyms(db: Session) -> dict[str, str]:
    """Voeg aliassen uit materialen, referenties en materieel toe als zoek-synoniemen."""
    synonyms: dict[str, str] = {}

    for material in db.query(Material).filter(Material.active.is_(True)).all():
        labels = json.loads(material.language_labels_json or "{}")
        target = (labels.get("nl") or MATERIAL_NL.get(material.canonical_name, material.canonical_name)).lower()
        for alias in [material.canonical_name, *_load_aliases(material.aliases_json), *labels.values()]:
            key = str(alias).strip().lower()
            if len(key) > 2 and key != target:
                synonyms.setdefault(key, target)

    for item in db.query(ReferenceItem).filter(ReferenceItem.active.is_(True)).all():
        labels = json.loads(item.language_labels_json or "{}")
        target = (labels.get("nl") or item.canonical_name).lower()
        for alias in [item.canonical_name, *_load_aliases(item.aliases_json), *labels.values()]:
            key = str(alias).strip().lower()
            if len(key) > 2 and key != target:
                synonyms.setdefault(key, target)

    for equip in db.query(Equipment).filter(Equipment.active.is_(True)).all():
        target = (equip.sap_code or equip.specifications or "").strip().lower()
        if not target:
            continue
        for alias in _load_aliases(equip.aliases_json):
            key = str(alias).strip().lower()
            if len(key) > 3 and key != target:
                synonyms.setdefault(key, target)

    return synonyms


def _merged_synonyms(db: Session | None) -> dict[str, str]:
    merged = dict(_load_static_synonyms())
    if db is not None:
        for src, dst in _db_synonyms(db).items():
            merged.setdefault(src, dst)
    return merged


def normalize_synonyms(text: str, db: Session | None = None) -> tuple[str, list[tuple[str, str]]]:
    """Vervang bekende synoniemen; retourneer genormaliseerde tekst + toegepaste vervangingen."""
    synonyms = _merged_synonyms(db)
    if not synonyms:
        return text, []
    lower = text.lower()
    applied: list[tuple[str, str]] = []
    for src, dst in sorted(synonyms.items(), key=lambda x: len(x[0]), reverse=True):
        if src in lower:
            pattern = re.compile(re.escape(src), re.IGNORECASE)
            text = pattern.sub(dst, text, count=1)
            lower = text.lower()
            applied.append((src, dst))
    return text, applied


def _dimension_suffix(text: str) -> str:
    """Behoud afmetings-/lengtedeel uit de query voor suggestie-waarden."""
    dim_match = re.search(
        r"(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?){0,2}(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?\s*(?:mm|cm|m)?)",
        text,
        re.IGNORECASE,
    )
    if dim_match:
        return dim_match.group(1).strip()
    profile_dim = re.search(
        r"\b((?:UNP|UPN|UPE|IPE|HEA|HEB|HEM|IPN|INP|SHS|RHS|CHS)\s*\d+.*?)$",
        text,
        re.IGNORECASE,
    )
    if profile_dim:
        return profile_dim.group(1).strip()
    length = re.search(r"(?:l\s*[=:]?\s*)?(\d+(?:[.,]\d+)?\s*(?:mm|cm|m)\b)", text, re.IGNORECASE)
    if length:
        return length.group(0).strip()
    return ""


def _merge_label(base: str, original_query: str) -> str:
    suffix = _dimension_suffix(original_query)
    if not suffix:
        return base.strip()
    if suffix.lower() in base.lower():
        return base.strip()
    return f"{base.strip()} {suffix}".strip()


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1}


def _score_tokens(query_tokens: set[str], haystack: str) -> float:
    if not query_tokens:
        return 0.0
    hay_tokens = _tokens(haystack)
    if not hay_tokens:
        return 0.0
    overlap = len(query_tokens & hay_tokens)
    score = overlap / max(len(query_tokens), 1)
    hay_lower = haystack.lower()
    joined = " ".join(query_tokens)
    if joined in hay_lower or hay_lower in joined:
        score += 2
    return score


def _substring_alias_score(query_lower: str, aliases: list[str]) -> float:
    best = 0.0
    for alias in aliases:
        alias_lower = str(alias).strip().lower()
        if not alias_lower or len(alias_lower) < 2:
            continue
        if alias_lower in query_lower:
            best = max(best, 2.5 + len(alias_lower) / max(len(query_lower), 1))
    return best


def _collect_terms(*parts: str | None) -> str:
    return " ".join(p for p in parts if p)


def _material_terms(material: Material) -> list[str]:
    labels = json.loads(material.language_labels_json or "{}")
    return [
        material.canonical_name,
        *_load_aliases(material.aliases_json),
        *labels.values(),
    ]


def _search_equipment(db: Session, query: str, normalized: str, query_tokens: set[str]) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for item in db.query(Equipment).filter(Equipment.active.is_(True)).all():
        labels = json.loads(item.language_labels_json or "{}")
        alias_list = [
            item.sap_code or "",
            item.specifications,
            *_load_aliases(item.aliases_json),
            *labels.values(),
        ]
        terms = _collect_terms(*alias_list)
        score = max(
            _score_tokens(query_tokens, terms),
            _substring_alias_score(query.lower(), alias_list),
            _substring_alias_score(normalized.lower(), alias_list),
        )
        norm_lower = normalized.lower()
        if "forklift" in norm_lower:
            if "forklift" in terms.lower():
                score += 5
            elif score < 2:
                continue
        if score <= 0:
            continue
        label = item.sap_code or item.specifications
        hits.append(
            SearchHit(
                id=f"equipment:{item.id}",
                source="equipment",
                label=label,
                sublabel=item.specifications if item.sap_code else f"{item.weight_kg} kg",
                value=_merge_label(label, query),
                score=score,
            )
        )
    return hits


def _search_profiles(db: Session, query: str, normalized: str, query_tokens: set[str], dims) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for profile in db.query(Profile).filter(Profile.active.is_(True)).all():
        label = f"{profile.profile_type} {profile.size_label}"
        alias_list = [label, profile.size_label, *_load_aliases(profile.aliases_json), profile.material or ""]
        terms = _collect_terms(*alias_list)
        score = max(
            _score_tokens(query_tokens, terms),
            _substring_alias_score(query.lower(), alias_list),
            _substring_alias_score(normalized.lower(), alias_list),
        )
        if dims.profile_size and dims.profile_size.lower() in terms.lower():
            score += 4
        if score <= 0:
            continue
        hits.append(
            SearchHit(
                id=f"profile:{profile.id}",
                source="profile",
                label=label,
                sublabel=f"{profile.kg_per_meter} kg/m · {profile.material}",
                value=_merge_label(label, query),
                score=score,
            )
        )
    return hits


def _search_materials(db: Session, query: str, query_tokens: set[str]) -> list[Material]:
    lower = query.lower()
    matched: list[tuple[Material, float]] = []
    for material in db.query(Material).filter(Material.active.is_(True)).all():
        terms = _material_terms(material)
        score = max(_score_tokens(query_tokens, _collect_terms(*terms)), _substring_alias_score(lower, terms))
        if score > 0:
            matched.append((material, score))
    matched.sort(key=lambda x: x[1], reverse=True)
    return [m for m, _ in matched[:4]]


def _search_reference(db: Session, query: str, normalized: str, query_tokens: set[str]) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for item in db.query(ReferenceItem).filter(ReferenceItem.active.is_(True)).all():
        labels = json.loads(item.language_labels_json or "{}")
        alias_list = [item.canonical_name, *_load_aliases(item.aliases_json), *labels.values()]
        terms = _collect_terms(*alias_list)
        score = max(
            _score_tokens(query_tokens, terms),
            _substring_alias_score(query.lower(), alias_list),
            _substring_alias_score(normalized.lower(), alias_list),
        )
        if score <= 0:
            continue
        display = labels.get("nl") or item.canonical_name
        hits.append(
            SearchHit(
                id=f"reference:{item.id}",
                source="reference",
                label=display,
                sublabel=f"{item.reference_weight_kg} kg",
                value=_merge_label(display, query),
                score=score + 1,
            )
        )
    return hits


def _template_suggestions(query: str, normalized: str, materials: list[Material], db: Session) -> list[SearchHit]:
    hits: list[SearchHit] = []
    product_type = detect_product_type(normalized)
    if not product_type:
        return hits

    product_nl = PRODUCT_LABELS_NL.get(product_type, product_type.replace("_", " "))
    suffix = _dimension_suffix(query)
    dim_hint = suffix or "bijv. 80x80x8x6000"

    if materials:
        for material in materials:
            labels = json.loads(material.language_labels_json or "{}")
            mat_nl = labels.get("nl") or MATERIAL_NL.get(material.canonical_name, material.canonical_name)
            mat_lower = mat_nl.lower()
            prod_lower = product_nl.lower()
            if mat_lower == prod_lower or prod_lower in mat_lower:
                base = mat_nl
            else:
                base = f"{mat_nl} {product_nl}".strip()
            value = f"{base} {suffix}".strip() if suffix else base
            hits.append(
                SearchHit(
                    id=f"template:{material.canonical_name}:{product_type}",
                    source="template",
                    label=base.title() if mat_nl.islower() else base,
                    sublabel=f"Voeg afmetingen toe: {dim_hint}" if not suffix else f"Afmetingen: {suffix}",
                    value=value,
                    score=8.0,
                )
            )
    else:
        base = product_nl
        value = f"{base} {suffix}".strip() if suffix else base
        hits.append(
            SearchHit(
                id=f"template::{product_type}",
                source="template",
                label=base.title(),
                sublabel=f"Voeg afmetingen toe: {dim_hint}" if not suffix else f"Afmetingen: {suffix}",
                value=value,
                score=6.0,
            )
        )

    _, applied = normalize_synonyms(query, db)
    if applied and hits:
        hits[0].score = max(hits[0].score, 9.0)
    return hits


def search_catalog(db: Session, query: str, limit: int = 25) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if len(query) < 2:
        return []

    normalized, _ = normalize_synonyms(query, db)
    query_tokens = _tokens(normalized) | _tokens(query)
    dims = extract_dimensions(normalized)

    hits: list[SearchHit] = []
    hits.extend(_template_suggestions(query, normalized, _search_materials(db, normalized, query_tokens), db))
    hits.extend(_search_equipment(db, query, normalized, query_tokens))
    hits.extend(_search_profiles(db, query, normalized, query_tokens, dims))
    hits.extend(_search_reference(db, query, normalized, query_tokens))

    seen: set[str] = set()
    unique: list[SearchHit] = []
    for hit in sorted(hits, key=lambda h: h.score, reverse=True):
        key = hit.value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
        if len(unique) >= limit:
            break

    return [h.to_dict() for h in unique]
