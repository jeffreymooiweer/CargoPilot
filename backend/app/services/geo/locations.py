"""Search service for airports, ports and railway stations.

The seeds (backend/seed/locations/*.json) come from public sources:
- OurAirports (public domain) — large and medium airports with an IATA code
- UN/LOCODE (UNECE) — locations with a port function
- Trainline EU stations (ODbL) — main stations

The data is loaded lazily into memory; no database is needed.
"""
from __future__ import annotations

import json
import threading
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

LOCATION_TYPES = ("airport", "port", "station")

_SEED_FILES = {
    "airport": "airports.json",
    "port": "ports.json",
    "station": "stations.json",
}

_lock = threading.Lock()
_cache: dict[str, list[dict]] = {}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def _locations_dir() -> Path:
    return get_settings().seed_dir / "locations"


def _load(location_type: str) -> list[dict]:
    with _lock:
        if location_type not in _cache:
            path = _locations_dir() / _SEED_FILES[location_type]
            entries = json.loads(path.read_text(encoding="utf-8"))
            for entry in entries:
                entry["_search"] = _normalize(
                    " ".join(
                        str(entry.get(key) or "")
                        for key in ("name", "code", "icao", "city", "country")
                    )
                )
            _cache[location_type] = entries
    return _cache[location_type]


def _score(entry: dict, query: str) -> int:
    """Higher = better match. 0 = no match."""
    code = _normalize(str(entry.get("code") or ""))
    icao = _normalize(str(entry.get("icao") or ""))
    name = _normalize(str(entry.get("name") or ""))
    city = _normalize(str(entry.get("city") or ""))
    if query in (code, icao):
        return 100
    if code.startswith(query) or icao.startswith(query):
        return 80
    if name.startswith(query) or city.startswith(query):
        return 60
    if any(word.startswith(query) for word in name.split() + city.split()):
        return 40
    if query in entry["_search"]:
        return 20
    return 0


def search_locations(
    query: str,
    types: list[str] | None = None,
    country: str | None = None,
    limit: int = 10,
) -> list[dict]:
    query_norm = _normalize(query.strip())
    if len(query_norm) < 2:
        return []
    wanted = [t for t in (types or LOCATION_TYPES) if t in LOCATION_TYPES]
    country_norm = (country or "").strip().upper()

    scored: list[tuple[int, dict]] = []
    for location_type in wanted:
        for entry in _load(location_type):
            if country_norm and entry.get("country") != country_norm:
                continue
            score = _score(entry, query_norm)
            if score:
                scored.append((score, {**{k: v for k, v in entry.items() if k != "_search"}, "type": location_type}))
    scored.sort(key=lambda item: (-item[0], item[1]["name"]))
    return [entry for _, entry in scored[:limit]]


def location_by_code(code: str, types: list[str] | None = None) -> dict | None:
    """The one location a code names, or nothing.

    A UN/LOCODE, an IATA code or a station number is the only part of a
    formatted location — ``Rotterdam (NLRTM), NL`` — that survives editing,
    so it is what the route reader looks up. An exact match only: a prefix
    is a search, not a name.
    """
    wanted = _normalize(code.strip())
    if not wanted:
        return None
    for location_type in (t for t in (types or LOCATION_TYPES) if t in LOCATION_TYPES):
        for entry in _load(location_type):
            if _normalize(str(entry.get("code") or "")) == wanted:
                return {**{k: v for k, v in entry.items() if k != "_search"}, "type": location_type}
    return None


@lru_cache
def location_counts() -> dict[str, int]:
    return {location_type: len(_load(location_type)) for location_type in LOCATION_TYPES}
