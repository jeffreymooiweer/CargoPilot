import json
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.user import Material
from app.services.catalog_sync.sources import EUROCODE_MATERIAL_SOURCE

logger = logging.getLogger(__name__)

EXTERNAL_SOURCE_PREFIXES = ("github:", "eurocodepy:", "nist:", "seed:external", "eurocode:")


@dataclass
class MaterialRecord:
    canonical_name: str
    category: str
    density_kg_m3: float
    density_min_kg_m3: float | None = None
    density_max_kg_m3: float | None = None
    condition: str | None = None
    language_labels: dict[str, str] | None = None
    aliases: list[str] | None = None
    source: str | None = None
    notes: str | None = None


def parse_bundled_materials(raw: str) -> list[MaterialRecord]:
    items = json.loads(raw)
    records: list[MaterialRecord] = []
    for item in items:
        records.append(
            MaterialRecord(
                canonical_name=item["canonical_name"],
                category=item["category"],
                density_kg_m3=item["density_kg_m3"],
                density_min_kg_m3=item.get("density_min_kg_m3"),
                density_max_kg_m3=item.get("density_max_kg_m3"),
                condition=item.get("condition"),
                language_labels=item.get("language_labels", {}),
                aliases=item.get("aliases", []),
                source=item.get("source"),
                notes=item.get("notes"),
            )
        )
    return records


def enrich_from_eurocode(records: list[MaterialRecord], eurocode_json: dict) -> list[MaterialRecord]:
    materials = eurocode_json.get("Eurocodes", {}).get("Materials", {})
    steel_mass = materials.get("Steel", {}).get("Parameters", {}).get("mass")
    if steel_mass:
        _upsert_record(records, "steel", density_kg_m3=float(steel_mass), source=EUROCODE_MATERIAL_SOURCE)
    timber = materials.get("Timber", {}).get("Grade", {})
    c24 = timber.get("C24", {})
    if c24.get("rhom"):
        _upsert_record(
            records,
            "spruce",
            density_kg_m3=float(c24["rhom"]),
            density_min_kg_m3=float(c24.get("rhok", c24["rhom"])),
            source=EUROCODE_MATERIAL_SOURCE,
        )
    gl24 = timber.get("GL24h", {})
    if gl24.get("rhom"):
        _upsert_record(
            records,
            "glulam_gl24h",
            density_kg_m3=float(gl24["rhom"]),
            source=EUROCODE_MATERIAL_SOURCE,
        )
    return records


def _upsert_record(
    records: list[MaterialRecord],
    canonical_name: str,
    *,
    density_kg_m3: float,
    density_min_kg_m3: float | None = None,
    source: str | None = None,
) -> None:
    for record in records:
        if record.canonical_name == canonical_name:
            record.density_kg_m3 = density_kg_m3
            if density_min_kg_m3 is not None:
                record.density_min_kg_m3 = density_min_kg_m3
            if source:
                record.source = source
            return
    records.append(
        MaterialRecord(
            canonical_name=canonical_name,
            category="metal" if canonical_name == "steel" else "wood",
            density_kg_m3=density_kg_m3,
            density_min_kg_m3=density_min_kg_m3,
            source=source,
        )
    )


def _is_external_managed(material: Material) -> bool:
    if not material.source:
        return True
    lower = material.source.lower()
    return lower.startswith(EXTERNAL_SOURCE_PREFIXES) or "eurocode" in lower or "github" in lower


def upsert_materials(db: Session, records: list[MaterialRecord]) -> tuple[int, int]:
    added = 0
    updated = 0
    for record in records:
        existing = db.query(Material).filter(Material.canonical_name == record.canonical_name).first()
        if existing:
            if not _is_external_managed(existing):
                continue
            existing.category = record.category
            existing.density_kg_m3 = record.density_kg_m3
            existing.density_min_kg_m3 = record.density_min_kg_m3
            existing.density_max_kg_m3 = record.density_max_kg_m3
            existing.condition = record.condition
            if record.language_labels:
                existing.language_labels_json = json.dumps(record.language_labels)
            if record.aliases:
                existing.aliases_json = json.dumps(record.aliases)
            existing.source = record.source
            existing.notes = record.notes
            existing.active = True
            updated += 1
        else:
            db.add(
                Material(
                    canonical_name=record.canonical_name,
                    category=record.category,
                    density_kg_m3=record.density_kg_m3,
                    density_min_kg_m3=record.density_min_kg_m3,
                    density_max_kg_m3=record.density_max_kg_m3,
                    condition=record.condition,
                    language_labels_json=json.dumps(record.language_labels or {}),
                    aliases_json=json.dumps(record.aliases or []),
                    source=record.source,
                    notes=record.notes,
                    active=True,
                )
            )
            added += 1
    return added, updated


def merge_seed_material_aliases(db: Session, records: list[MaterialRecord]) -> None:
    """Behoud extra aliassen uit de lokale seed wanneer canonical_name overeenkomt."""
    by_name = {r.canonical_name: r for r in records}
    for material in db.query(Material).all():
        if material.canonical_name not in by_name:
            continue
        seed_aliases = set(json.loads(material.aliases_json or "[]"))
        record = by_name[material.canonical_name]
        merged = list(dict.fromkeys([*(record.aliases or []), *seed_aliases]))
        record.aliases = merged
        labels = json.loads(material.language_labels_json or "{}")
        if labels:
            record.language_labels = {**(record.language_labels or {}), **labels}
