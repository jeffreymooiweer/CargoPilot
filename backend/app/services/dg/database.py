"""Offline UN number and packaging database.

Sources (see README):
- ADR 2023 Table A (derived from the official UNECE publication): class,
  classification code, packing group, labels, LQ/EQ, packing instructions,
  transport category, tunnel code, hazard number.
- 49 CFR 172.101 (eCFR, public domain): English proper shipping names.
- ADR 2025, Dutch edition, table A column (2): the Dutch proper shipping names,
  read by ``scripts/extract_adr_names.py``. They are attached here rather than
  in the table itself, because they come from a later edition than the export
  the rest of the entry is built on.
- UN packaging codes per ADR 6.1.2 / 6.5.1.4 / 6.6.2.

Note: this is a factual compilation as an aid to filling in; the current
ADR/IMDG/IATA edition remains authoritative.
"""
from __future__ import annotations

import json
import threading
import unicodedata
from pathlib import Path

from app.services.dg import amendment_42_24
from app.services.dg.enrichment import clean_value, enrich_un_entry, parse_hazards
from app.services.dg.names_nl import dutch_name
from app.services.dg.naming import proper_shipping_name

_SEED_DIR = Path(__file__).resolve().parents[3] / "seed" / "dg"

_lock = threading.Lock()
_un_cache: list[dict] | None = None
_pack_cache: list[dict] | None = None


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def _imdg_only_entries(known: set[str]) -> list[dict]:
    """UN numbers IMDG 42-24 adds that ADR 2025 does not know yet.

    Sodium-ion batteries and the new vehicle entries come from the 23rd edition
    of the UN Model Regulations. That is already in IMDG 42-24, but only in a
    future ADR edition. Whoever ships them by sea has to be able to find them;
    hence they are here, explicitly marked as IMDG-only.
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
            # The DGL names the division itself; Table A does so via the labels.
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
                # The Dutch name comes from a separate seed, and searching on it
                # is the point of having it: whoever types "zoutzuur" used to get
                # nothing at all, because the index held only English and German.
                entry["name_nl"] = dutch_name(entry["un"])
                entry["_search"] = _normalize(
                    f"{entry.get('name_en', '')} {entry.get('name_de', '')} "
                    f"{entry['name_nl']}"
                )
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
            # A name the entry *starts* with outranks one it merely contains, and
            # that has to hold for each of the three languages. Weighing only the
            # English put "zoutzuur" behind every entry with the word somewhere in
            # the middle, while it is the name of UN 1789 itself.
            names = [_normalize(entry.get(key) or "")
                     for key in ("name_en", "name_de", "name_nl")]
            if any(name.startswith(text) for name in names if name):
                scored.append((60, entry))
            elif any(word.startswith(text) for word in hay.split()):
                scored.append((40, entry))
            elif text in hay:
                scored.append((20, entry))

    scored.sort(key=lambda item: (-item[0], item[1]["un"], item[1].get("packing_group") or ""))
    # The suggestion carries the name that ends up on the document, so it has to
    # follow the same language choice as the export.
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
    """Same shape as the FreightUtils lookup, as an offline fallback."""
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
    """True when ADR Table A does not admit the substance for carriage."""
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
