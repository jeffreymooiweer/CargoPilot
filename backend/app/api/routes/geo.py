"""Geo-endpoints: locatie-typeahead (luchthavens/havens/stations) en adres-autocomplete.

Adres-autocomplete proxyt naar een Photon-compatibele API (standaard photon.komoot.io,
OpenStreetMap-data). Instelbaar via GEO_ADDRESS_API_URL; faalt zacht zodat de wizard
bruikbaar blijft zonder internettoegang.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.models.user import User
from app.services.geo.locations import LOCATION_TYPES, search_locations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/locations")
def geo_locations(
    q: str = Query(..., min_length=2, max_length=80),
    type: str | None = Query(default=None, description="Kommagescheiden: airport,port,station"),
    country: str | None = Query(default=None, min_length=2, max_length=2),
    limit: int = Query(default=10, ge=1, le=25),
    user: User = Depends(get_current_user),
):
    types = None
    if type:
        types = [t.strip() for t in type.split(",") if t.strip() in LOCATION_TYPES]
    return {"results": search_locations(q, types=types, country=country, limit=limit)}


@router.get("/address")
def geo_address(
    q: str = Query(..., min_length=3, max_length=200),
    lang: str = Query(default="en", min_length=2, max_length=2),
    limit: int = Query(default=6, ge=1, le=15),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    params = {"q": q, "limit": limit, "lang": lang if lang in ("en", "de", "fr") else "en"}
    headers = {"User-Agent": "CargoPilot (+https://github.com/jeffreymooiweer/CargoPilot)"}
    try:
        with httpx.Client(timeout=settings.geo_address_timeout_seconds, headers=headers) as client:
            response = client.get(settings.geo_address_api_url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Adres-API niet bereikbaar: %s", exc)
        return {"results": [], "available": False}

    results = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        name = props.get("name") or ""
        street = props.get("street") or (name if props.get("housenumber") else "")
        street_line = " ".join(p for p in (street, props.get("housenumber")) if p)
        label_parts = [name] if name and name != street else []
        label_parts += [street_line, props.get("postcode"), props.get("city"), props.get("country")]
        results.append(
            {
                "label": ", ".join(p for p in label_parts if p),
                "name": name,
                "street": street,
                "housenumber": props.get("housenumber") or "",
                "postcode": props.get("postcode") or "",
                "city": props.get("city") or "",
                "state": props.get("state") or "",
                "country": props.get("country") or "",
                "countrycode": props.get("countrycode") or "",
            }
        )
    return {"results": results, "available": True}
