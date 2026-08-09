"""IMDG-code Amendment 42-24 als verschillenlaag over de 41-22-gegevens.

De app draagt ADR 2025 als basistabel en de Cantell UN-kaarten (41-22) als
stof-specifieke IMDG-laag. Sinds 1 januari 2026 is 42-24 verplicht. In plaats
van de hele dataset opnieuw op te bouwen — waarvoor de gepubliceerde tekst
nodig is — legt deze module de wijzigingen die uit de bron af te leiden zijn
bovenop de bestaande gegevens, en zegt er per stof bij wat er veranderd is.

Twee dingen bepalen wat hier wel en niet in staat:

- Wat de bron letterlijk noemt, staat erin. Wat zij niet noemt, is niet
  verzonnen; `not_covered` in het seed-bestand somt op wat buiten beeld blijft.
- Hoofdstuk 7.2 kent in 42-24 één wijziging: de herformulering van 7.2.6.1. De
  scheidingstabel van 7.2.4, de vrijstellingstabellen van 7.2.6.3, de
  compatibiliteitsmatrix van 7.2.7.1.4 en de scheidingsgroepen van 3.1.4.4
  blijven ongewijzigd. Die tabellen zijn dus ook onder 42-24 juist, en worden
  niet langer als achterlopend gemarkeerd.

De gepubliceerde tekst van de code blijft leidend; dit is een invulhulp.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.core.languages import SUPPORTED, pick

_SEED = Path(__file__).resolve().parents[3] / "seed" / "dg" / "imdg_42_24.json"

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _cache
    with _lock:
        if _cache is None:
            try:
                _cache = json.loads(_SEED.read_text(encoding="utf-8"))
            except (OSError, ValueError):  # pragma: no cover - seed ontbreekt
                _cache = {}
    return _cache


def _digits(un: str) -> str:
    return "".join(ch for ch in str(un or "") if ch.isdigit()).zfill(4)


def amendment() -> str:
    return str(_load().get("amendment") or "")


def source() -> str:
    return str(_load().get("source") or "")


def verified_unchanged_sections() -> list[str]:
    """Secties waarvan de bron bevestigt dat 42-24 ze niet wijzigt."""
    data = _load().get("verified_unchanged") or {}
    return [item["section"] for item in data.get("sections", [])]


def new_un_numbers() -> list[dict[str, Any]]:
    """UN-nummers die 42-24 toevoegt en die in ADR 2025 nog niet bestaan."""
    return list(_load().get("new_un_numbers") or [])


def ems_additions() -> dict[str, dict[str, str]]:
    return dict((_load().get("ems_additions") or {}).get("entries") or {})


def _entry_for(un: str, packing_group: str = "") -> dict[str, Any]:
    """De wijziging voor dit UN-nummer, zo nodig per verpakkingsgroep.

    UN 1835 en UN 3423 verschillen per verpakkingsgroep: dezelfde stof, een
    andere vermelding. Wie de verpakkingsgroep niet meegeeft, krijgt alleen wat
    voor alle groepen geldt — nooit de striktere variant stilzwijgend.
    """
    change = (_load().get("amended_un_numbers") or {}).get(_digits(un))
    if not isinstance(change, dict):
        return {}
    by_group = change.get("by_packing_group")
    if not isinstance(by_group, dict):
        return change
    pg = str(packing_group or "").strip().upper()
    specific = by_group.get(pg)
    if isinstance(specific, dict):
        return {**{k: v for k, v in change.items() if k != "by_packing_group"}, **specific}
    return {k: v for k, v in change.items() if k != "by_packing_group"}


def changes_for(un: str, packing_group: str = "", language: str = "nl") -> list[str]:
    """Wat er voor deze stof onder 42-24 verandert, in gewone taal."""
    entry = _entry_for(un, packing_group)
    value = pick(
        {lang: entry.get(f"changes_{lang}") for lang in SUPPORTED}, language, []
    )
    return [str(line) for line in value if str(line).strip()]


def overlay_for(un: str, packing_group: str = "") -> dict[str, Any]:
    """De ruwe wijzigingsvelden voor een stof, zonder de toelichtende teksten."""
    entry = _entry_for(un, packing_group)
    return {k: v for k, v in entry.items() if not k.startswith("changes_")}


def apply_card_overlay(un: str, card: dict[str, Any], packing_group: str = "") -> dict[str, Any]:
    """Werk de gegevens van de 41-22-UN-kaart bij naar 42-24.

    Alleen toevoegen en corrigeren; er wordt niets weggehaald wat de bron niet
    expliciet intrekt. Een stuwagecode die er in 41-22 al stond blijft staan.
    """
    overlay = overlay_for(un, packing_group)
    if not overlay or not isinstance(card, dict):
        return card
    updated = dict(card)

    added = [c for c in overlay.get("stowage_codes_add") or []
             if c not in (updated.get("stowage_codes") or [])]
    if added:
        updated["stowage_codes"] = list(updated.get("stowage_codes") or []) + added

    if overlay.get("marine_pollutant"):
        updated["marine_pollutant"] = overlay["marine_pollutant"]

    if overlay.get("stowage_category"):
        updated["stowage_category"] = overlay["stowage_category"]

    if added or overlay.get("marine_pollutant") or overlay.get("stowage_category"):
        updated["amended_by"] = "IMDG 42-24"
    return updated


def document_requirement(un: str, language: str = "nl") -> dict[str, Any] | None:
    """Aanvullende documentvereiste per stof, zoals 5.4.1.5.18 voor UN 1361."""
    item = (_load().get("document_requirements") or {}).get(_digits(un))
    if not isinstance(item, dict):
        return None
    return {
        "section": item.get("section"),
        "text": pick(item, language),
        "fields": list(item.get("fields") or []),
    }


def general_document_requirements(language: str = "nl") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in _load().get("general_document_requirements") or []:
        out.append({
            "section": item.get("section"),
            "text": pick(item, language),
            "special_provisions": list(item.get("special_provisions") or []),
        })
    return out


def amended_sections(language: str = "nl") -> list[dict[str, Any]]:
    data = (_load().get("verified_unchanged") or {}).get("amended_sections") or []
    return [
        {"section": i.get("section"), "text": pick(i, language)}
        for i in data
    ]


def not_covered(language: str = "nl") -> list[str]:
    data = _load().get("not_covered") or {}
    items = pick({lang: data.get(f"items_{lang}") for lang in SUPPORTED}, language, [])
    return [str(x) for x in items]
