import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.catalog_sync.hollow_profiles import HollowProfileFile, load_hollow_profiles_from_files
from app.services.catalog_sync.materials import (
    enrich_from_eurocode,
    load_seed_material_records,
    merge_material_records,
    parse_bundled_materials,
    upsert_materials,
)
from app.services.catalog_sync.profiles import load_steel_profiles_from_csv_map, upsert_profiles
from app.services.catalog_sync.sources import (
    EUROCODE_HOLLOW_SOURCE,
    EUROCODE_MATERIALS_URL,
    HOLLOW_PROFILE_FILES,
    STEEL_PROFILE_TYPES,
    bundled_eurocode_hollow,
    bundled_eurocode_materials,
    bundled_seed_materials,
    bundled_steel_csv,
    eurocode_hollow_remote_url,
    steel_profile_remote_url,
)
from app.services.catalog_sync.wikidata import (
    WIKIDATA_MATERIAL_MAP,
    enrich_from_wikidata,
    fetch_wikidata_densities,
)

logger = logging.getLogger(__name__)

_status: dict[str, Any] = {
    "last_run_at": None,
    "success": None,
    "profiles_added": 0,
    "profiles_updated": 0,
    "materials_added": 0,
    "materials_updated": 0,
    "profile_count": 0,
    "material_count": 0,
    "sources": [],
    "errors": [],
    "used_offline_fallback": False,
}


def get_sync_status() -> dict[str, Any]:
    settings = get_settings()
    status_path = settings.data_dir / "catalog_sync_status.json"
    if status_path.exists():
        try:
            return json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return dict(_status)


def _save_status(status: dict[str, Any]) -> None:
    global _status
    _status = status
    settings = get_settings()
    status_path = settings.data_dir / "catalog_sync_status.json"
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not persist catalog sync status: %s", exc)


def _fetch_text(client: httpx.Client, url: str, timeout: float) -> str | None:
    try:
        response = client.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        logger.warning("Fetch failed for %s: %s", url, exc)
        return None


def _load_steel_csv_map(client: httpx.Client | None, timeout: float, use_network: bool) -> tuple[dict[str, str], bool]:
    csv_map: dict[str, str] = {}
    used_fallback = False
    settings = get_settings()
    for profile_type in STEEL_PROFILE_TYPES:
        remote = None
        if use_network and client is not None:
            remote = _fetch_text(client, steel_profile_remote_url(profile_type), timeout)
        if remote:
            csv_map[profile_type] = remote
            continue
        bundled = bundled_steel_csv(profile_type, settings.seed_dir)
        if bundled.exists():
            csv_map[profile_type] = bundled.read_text(encoding="utf-8")
            used_fallback = True
            logger.info("Using bundled steel CSV for %s", profile_type)
    return csv_map, used_fallback


def _load_hollow_files(client: httpx.Client | None, timeout: float, use_network: bool) -> tuple[list[HollowProfileFile], bool]:
    files: list[HollowProfileFile] = []
    used_fallback = False
    settings = get_settings()
    for name in HOLLOW_PROFILE_FILES:
        content = None
        if use_network and client is not None:
            content = _fetch_text(client, eurocode_hollow_remote_url(name), timeout)
        if not content:
            bundled = bundled_eurocode_hollow(settings.seed_dir, name)
            if bundled.exists():
                content = bundled.read_text(encoding="utf-8")
                used_fallback = True
        if content:
            files.append(HollowProfileFile(name=name, content=content))
    return files, used_fallback


def sync_catalogs(db: Session, *, use_network: bool = True) -> dict[str, Any]:
    settings = get_settings()
    timeout = settings.catalog_sync_timeout_seconds
    errors: list[str] = []
    sources: list[str] = []
    used_offline_fallback = False

    with httpx.Client(follow_redirects=True) as client:
        csv_map, steel_fallback = _load_steel_csv_map(
            client if use_network else None, timeout, use_network
        )
        hollow_files, hollow_fallback = _load_hollow_files(
            client if use_network else None, timeout, use_network
        )
        used_offline_fallback = steel_fallback or hollow_fallback

        eurocode_json: dict[str, Any] = {}
        bundled_materials_path = bundled_eurocode_materials(settings.seed_dir)
        external_materials_raw = bundled_materials_path.read_text(encoding="utf-8")
        sources.append("seed/materials.json")
        sources.append(bundled_materials_path.name)

        if use_network:
            remote_eurocode = _fetch_text(client, EUROCODE_MATERIALS_URL, timeout)
            if remote_eurocode:
                try:
                    eurocode_json = json.loads(remote_eurocode)
                    sources.append(EUROCODE_MATERIALS_URL)
                except json.JSONDecodeError:
                    errors.append("Kon eurocodes.json niet parsen")
            else:
                used_offline_fallback = True

            wikidata = fetch_wikidata_densities(client, list(WIKIDATA_MATERIAL_MAP), timeout)
            if wikidata:
                sources.append("wikidata.org (SPARQL P2054)")
        else:
            wikidata = []

    profile_records = load_steel_profiles_from_csv_map(csv_map)
    if profile_records:
        sources.append("steelprofiles_api (UPN/IPE/HEA/HEB/HEM/IPN)")
    else:
        errors.append("Geen hot-rolled staalprofielen geladen")

    hollow_records = load_hollow_profiles_from_files(hollow_files)
    if hollow_records:
        sources.append(EUROCODE_HOLLOW_SOURCE)
    else:
        errors.append("Geen koker/buisprofielen geladen")

    all_profile_records = profile_records + hollow_records

    seed_materials = load_seed_material_records(bundled_seed_materials(settings.seed_dir))
    external_materials = parse_bundled_materials(
        external_materials_raw, default_source="en1991:reference"
    )
    material_records = merge_material_records(seed_materials, external_materials)
    if eurocode_json:
        material_records = enrich_from_eurocode(material_records, eurocode_json)
    if wikidata:
        material_records = enrich_from_wikidata(material_records, wikidata)

    from app.services.catalog_sync.materials import merge_seed_material_aliases

    merge_seed_material_aliases(db, material_records)

    profiles_added, profiles_updated = upsert_profiles(db, all_profile_records)
    materials_added, materials_updated = upsert_materials(db, material_records)
    db.commit()

    from app.models.user import Material, Profile

    status = {
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "success": len(all_profile_records) > 0 and len(material_records) > 0,
        "profiles_added": profiles_added,
        "profiles_updated": profiles_updated,
        "materials_added": materials_added,
        "materials_updated": materials_updated,
        "profile_count": db.query(Profile).filter(Profile.active.is_(True)).count(),
        "material_count": db.query(Material).filter(Material.active.is_(True)).count(),
        "sources": sources,
        "errors": errors,
        "used_offline_fallback": used_offline_fallback,
    }
    _save_status(status)
    logger.info(
        "Catalog sync complete: +%s/~%s profiles, +%s/~%s materials (%s sources)",
        profiles_added,
        profiles_updated,
        materials_added,
        materials_updated,
        len(sources),
    )
    return status
