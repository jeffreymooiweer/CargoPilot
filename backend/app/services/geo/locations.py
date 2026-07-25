"""Zoekservice voor luchthavens, havens en treinstations.

De seeds (backend/seed/locations/*.json) komen uit openbare bronnen:
- OurAirports (public domain) — grote en middelgrote luchthavens met IATA-code
- UN/LOCODE (UNECE) — locaties met havenfunctie
- Trainline EU stations (ODbL) — hoofdstations

De data wordt lazy in het geheugen geladen; er is geen database nodig.
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
    """Hoger = betere match. 0 = geen match."""
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


@lru_cache
def location_counts() -> dict[str, int]:
    return {location_type: len(_load(location_type)) for location_type in LOCATION_TYPES}
