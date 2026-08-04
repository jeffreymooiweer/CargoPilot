"""Offline UN-nummer- en verpakkingendatabase.

Bronnen (zie README):
- ADR 2023 Tabel A (afgeleid uit officiële UNECE-publicatie): klasse,
  classificatiecode, verpakkingsgroep, etiketten, LQ/EQ, verpakkingsinstructies,
  vervoerscategorie, tunnelcode, gevaarsnummer.
- 49 CFR 172.101 (eCFR, public domain): Engelse proper shipping names.
- UN-verpakkingscodes volgens ADR 6.1.2 / 6.5.1.4 / 6.6.2.

Let op: dit is een feitelijke compilatie als invulhulp; de actuele ADR/IMDG/IATA-
uitgave blijft leidend.
"""
from __future__ import annotations

import json
import threading
import unicodedata
from pathlib import Path

from app.services.dg import amendment_42_24
from app.services.dg.enrichment import clean_value, enrich_un_entry, parse_hazards
from app.services.dg.naming import proper_shipping_name

_SEED_DIR = Path(__file__).resolve().parents[3] / "seed" / "dg"

_lock = threading.Lock()
_un_cache: list[dict] | None = None
_pack_cache: list[dict] | None = None


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def _imdg_only_entries(known: set[str]) -> list[dict]:
    """UN-nummers die IMDG 42-24 toevoegt en die ADR 2025 nog niet kent.

    Natrium-ionbatterijen en de nieuwe voertuigvermeldingen komen uit de 23e
    editie van de UN-modelvoorschriften. Die zit al in IMDG 42-24, maar pas in
    een volgende ADR-uitgave. Wie ze over zee verscheept moet ze kunnen vinden;
    daarom staan ze hier, uitdrukkelijk gemerkt als alleen-IMDG.
    """
    entries: list[dict] = []
    for item in amendment_42_24.new_un_numbers():
        if item["un"] in known:
            continue
        hazard = str(item.get("class") or "")
        entries.append({
            "un": item["un"],
            "name_en": item.get("name_en", ""),
            "name_de": "",
            # De DGL noemt de divisie zelf; Tabel A doet dat via de etiketten.
            "class": hazard.split(".")[0] if hazard.startswith("1.") else hazard,
            "classification_code": hazard if hazard.startswith("1.") else "",
            "packing_group": item.get("packing_group", ""),
            "labels": hazard,
            "special_provisions": item.get("special_provisions", ""),
            "limited_quantity": item.get("limited_quantity", "0"),
            "excepted_quantity": item.get("excepted_quantity", "E0"),
            "packing_instructions": item.get("packing_instructions", ""),
            "transport_category": "",
            "tunnel_code": "",
            "hazard_number": "",
            "imdg_only": True,
            "source_note": "IMDG 42-24 — nog niet in ADR Tabel A",
        })
    return entries


def _load_un() -> list[dict]:
    global _un_cache
    with _lock:
        if _un_cache is None:
            entries = json.loads((_SEED_DIR / "un_numbers.json").read_text(encoding="utf-8"))
            entries += _imdg_only_entries({e["un"] for e in entries})
            for entry in entries:
                entry["_search"] = _normalize(f"{entry.get('name_en', '')} {entry.get('name_de', '')}")
            _un_cache = entries
    return _un_cache


def _load_packagings() -> list[dict]:
    global _pack_cache
    with _lock:
        if _pack_cache is None:
            entries = json.loads((_SEED_DIR / "packagings.json").read_text(encoding="utf-8"))
            for entry in entries:
                label = entry.get("label") or {}
                entry["_search"] = _normalize(f"{entry['code']} {label.get('nl', '')} {label.get('en', '')}")
            _pack_cache = entries
    return _pack_cache


def _public(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def search_un_numbers(
    query: str,
    limit: int = 12,
    language: str = "nl",
    profiles: list[str] | None = None,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []
    digits = "".join(ch for ch in query if ch.isdigit())
    text = _normalize(query)
    entries = _load_un()

    scored: list[tuple[int, dict]] = []
    if digits and digits == query.replace("UN", "").replace("un", "").strip():
        for entry in entries:
            if entry["un"] == digits.zfill(4):
                scored.append((100, entry))
            elif entry["un"].startswith(digits) or entry["un"].lstrip("0").startswith(digits):
                scored.append((80, entry))
    elif len(text) >= 2:
        for entry in entries:
            hay = entry["_search"]
            name = _normalize(entry.get("name_en") or entry.get("name_de") or "")
            if name.startswith(text):
                scored.append((60, entry))
            elif any(word.startswith(text) for word in hay.split()):
                scored.append((40, entry))
            elif text in hay:
                scored.append((20, entry))

    scored.sort(key=lambda item: (-item[0], item[1]["un"], item[1].get("packing_group") or ""))
    # De suggestie draagt de naam die op het document terechtkomt; die moet dus
    # dezelfde taalkeuze volgen als de export.
    return [
        {
            **_public(entry),
            **enrich_un_entry(entry, language),
            "proper_shipping_name": proper_shipping_name(entry, language, profiles),
        }
        for _, entry in scored[:limit]
    ]


def get_un_entries(un_number: str) -> list[dict]:
    digits = "".join(ch for ch in un_number if ch.isdigit()).zfill(4)
    return [_public(entry) for entry in _load_un() if entry["un"] == digits]


def offline_lookup(
    un_number: str, language: str = "nl", profiles: list[str] | None = None
) -> dict | None:
    """Zelfde vorm als de FreightUtils-lookup, als offline terugval."""
    entries = get_un_entries(un_number)
    if not entries:
        return None
    entry = entries[0]
    hazards = parse_hazards(entry)
    return {
        **enrich_un_entry(entry, language),
        "un_number": entry["un"],
        "proper_shipping_name": proper_shipping_name(entry, language, profiles),
        "class": hazards["division"],
        "subsidiary_risks": "+".join(hazards["subsidiary_risks"]),
        "classification_code": hazards["classification_code"],
        "packing_group": clean_value(entry.get("packing_group")),
        "packing_instruction": clean_value(entry.get("packing_instructions")).split(" ")[0] or None,
        "labels": clean_value(entry.get("labels")),
        "limited_quantity": clean_value(entry.get("limited_quantity")),
        "excepted_quantity": clean_value(entry.get("excepted_quantity")),
        "tunnel_restriction_code": f"({entry['tunnel_code']})" if entry.get("tunnel_code") else None,
        "transport_category": entry.get("transport_category"),
        "source": (
            f"CargoPilot offline seed ({entry['source_note']})"
            if entry.get("source_note")
            else "CargoPilot offline seed (ADR 2023 Tabel A / 49 CFR 172.101)"
        ),
        "variants": len(entries),
    }


def is_transport_forbidden(un_number: str) -> bool:
    """True wanneer ADR Tabel A de stof niet ten vervoer toelaat."""
    entries = get_un_entries(un_number)
    if not entries:
        return False
    return any("VERBOTEN" in str(entry.get("labels") or "").upper() for entry in entries)


def search_packagings(query: str = "", limit: int = 150) -> list[dict]:
    entries = _load_packagings()
    query = query.strip()
    if not query:
        return [_public(entry) for entry in entries[:limit]]
    text = _normalize(query)
    scored: list[tuple[int, dict]] = []
    for entry in entries:
        code = _normalize(entry["code"])
        if code == text:
            scored.append((100, entry))
        elif code.startswith(text):
            scored.append((80, entry))
        elif any(word.startswith(text) for word in entry["_search"].split()):
            scored.append((40, entry))
        elif text in entry["_search"]:
            scored.append((20, entry))
    scored.sort(key=lambda item: (-item[0], item[1]["code"]))
    return [_public(entry) for _, entry in scored[:limit]]
