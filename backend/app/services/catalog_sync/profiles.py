import csv
import io
import json
import logging
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.user import Profile
from app.services.catalog_sync.sources import STEEL_PROFILE_SOURCE, STEEL_PROFILE_TYPES

logger = logging.getLogger(__name__)

PROFILE_TYPE_ALIASES: dict[str, list[str]] = {
    "UPN": ["UNP"],
    "IPN": ["INP"],
}


@dataclass
class ProfileRecord:
    profile_type: str
    size_label: str
    kg_per_meter: float
    standard: str
    aliases: list[str]
    source: str
    notes: str | None = None


def _size_from_name(name: str, profile_type: str) -> str:
    prefix = profile_type.upper()
    upper = name.upper()
    if upper.startswith(prefix):
        return upper[len(prefix) :].lstrip("-_ ")
    match = re.search(r"(\d+(?:\.\d+)?)", name)
    return match.group(1) if match else name


def _build_aliases(profile_type: str, size: str) -> list[str]:
    aliases: list[str] = []
    types = [profile_type.upper(), *PROFILE_TYPE_ALIASES.get(profile_type.upper(), [])]
    for t in types:
        aliases.extend([f"{t} {size}", f"{t}{size}"])
    if profile_type.upper() == "UPN":
        aliases.extend([f"U-profiel {size}", f"U-channel {size}", f"U profiel {size}"])
    if profile_type.upper() == "IPE":
        aliases.extend([f"I-balk {size}", f"IPE-profiel {size}"])
    return list(dict.fromkeys(aliases))


def parse_steel_csv(profile_type: str, csv_text: str) -> list[ProfileRecord]:
    reader = csv.DictReader(io.StringIO(csv_text))
    records: list[ProfileRecord] = []
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        try:
            kg_per_m = float(row.get("G") or row.get("g") or "")
        except (TypeError, ValueError):
            logger.warning("Skipping %s row without valid G column: %s", profile_type, name)
            continue
        size = _size_from_name(name, profile_type)
        records.append(
            ProfileRecord(
                profile_type=profile_type.upper(),
                size_label=size,
                kg_per_meter=kg_per_m,
                standard="EN10365",
                aliases=_build_aliases(profile_type, size),
                source=STEEL_PROFILE_SOURCE,
                notes=f"Geïmporteerd uit {name}",
            )
        )
    return records


def _find_existing_profile(db: Session, profile_type: str, size_label: str) -> Profile | None:
    profile_type = profile_type.upper()
    size_label = size_label.strip()
    direct = (
        db.query(Profile)
        .filter(Profile.profile_type == profile_type, Profile.size_label == size_label)
        .first()
    )
    if direct:
        return direct
    alt_types = [profile_type, *PROFILE_TYPE_ALIASES.get(profile_type, [])]
    for alt in alt_types:
        found = (
            db.query(Profile)
            .filter(Profile.profile_type == alt, Profile.size_label == size_label)
            .first()
        )
        if found:
            return found
    return None


def upsert_profiles(db: Session, records: list[ProfileRecord]) -> tuple[int, int]:
    added = 0
    updated = 0
    for record in records:
        existing = _find_existing_profile(db, record.profile_type, record.size_label)
        if existing:
            if existing.source and not existing.source.startswith(("github:", "eurocodepy:", "seed:")):
                continue
            existing.profile_type = record.profile_type
            existing.kg_per_meter = record.kg_per_meter
            existing.material = "steel"
            existing.standard = record.standard
            existing.aliases_json = json.dumps(record.aliases)
            existing.source = record.source
            existing.notes = record.notes
            existing.active = True
            updated += 1
        else:
            db.add(
                Profile(
                    profile_type=record.profile_type,
                    size_label=record.size_label,
                    kg_per_meter=record.kg_per_meter,
                    material="steel",
                    standard=record.standard,
                    aliases_json=json.dumps(record.aliases),
                    source=record.source,
                    notes=record.notes,
                    active=True,
                )
            )
            added += 1
    return added, updated


def load_steel_profiles_from_csv_map(csv_map: dict[str, str]) -> list[ProfileRecord]:
    records: list[ProfileRecord] = []
    for profile_type in STEEL_PROFILE_TYPES:
        csv_text = csv_map.get(profile_type)
        if not csv_text:
            logger.warning("No CSV data for profile type %s", profile_type)
            continue
        records.extend(parse_steel_csv(profile_type, csv_text))
    return records
