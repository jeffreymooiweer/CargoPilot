import json
import logging
import re
from dataclasses import dataclass

from app.services.catalog_sync.profiles import ProfileRecord

logger = logging.getLogger(__name__)

HOLLOW_PROFILE_SOURCE = "github:kristapsfreibergs/eurocodepy (EN 10210/10219, kg/m)"
HOLLOW_PROFILE_FILES = ("shs_profiles_euro", "rhs_profiles_euro", "chs_profiles_euro")


@dataclass
class HollowProfileFile:
    name: str
    content: str


def _normalize_dims(raw: str) -> str:
    parts = raw.lower().split("x")
    return "x".join(part.replace("_", ".") for part in parts)


def _parse_section(section: str) -> tuple[str, str] | None:
    match = re.match(r"^(SHS|RHS|CHS)(.+)$", section.strip(), re.I)
    if not match:
        return None
    profile_type = match.group(1).upper()
    size_label = _normalize_dims(match.group(2))
    return profile_type, size_label


def _build_hollow_aliases(profile_type: str, size_label: str) -> list[str]:
    aliases = [
        f"{profile_type} {size_label}",
        f"{profile_type}{size_label}",
        size_label,
    ]
    if profile_type == "SHS":
        aliases.extend(
            [
                f"koker {size_label}",
                f"kokerprofiel {size_label}",
                f"vierkant koker {size_label}",
                f"square tube {size_label}",
            ]
        )
    elif profile_type == "RHS":
        aliases.extend(
            [
                f"koker {size_label}",
                f"kokerprofiel {size_label}",
                f"rechthoekig koker {size_label}",
                f"rectangular tube {size_label}",
            ]
        )
    elif profile_type == "CHS":
        aliases.extend(
            [
                f"buis {size_label}",
                f"ronde buis {size_label}",
                f"pipe {size_label}",
                f"CHS {size_label}",
            ]
        )
    return list(dict.fromkeys(aliases))


def parse_hollow_profiles_json(raw: str, source: str = HOLLOW_PROFILE_SOURCE) -> list[ProfileRecord]:
    items = json.loads(raw)
    records: list[ProfileRecord] = []
    for item in items:
        section = item.get("Section") or ""
        parsed = _parse_section(section)
        if not parsed:
            continue
        profile_type, size_label = parsed
        try:
            kg_per_m = float(item.get("m") or "")
        except (TypeError, ValueError):
            logger.warning("Skipping hollow profile without kg/m: %s", section)
            continue
        records.append(
            ProfileRecord(
                profile_type=profile_type,
                size_label=size_label,
                kg_per_meter=kg_per_m,
                standard="EN10210" if profile_type != "RHS" else "EN10219",
                aliases=_build_hollow_aliases(profile_type, size_label),
                source=source,
                notes=f"Eurocode hollow section {section}",
            )
        )
    return records


def load_hollow_profiles_from_files(files: list[HollowProfileFile]) -> list[ProfileRecord]:
    records: list[ProfileRecord] = []
    for file in files:
        if not file.content:
            continue
        records.extend(parse_hollow_profiles_json(file.content))
    return records
