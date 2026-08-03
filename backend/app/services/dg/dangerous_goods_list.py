"""De Dangerous Goods List van IMDG-code Amendment 42-24, per UN-nummer.

Tot nu toe kende de app kolom 16a en 16b alleen voor de stoffen waarvan
toevallig een UN-kaart bestond, en dan nog zoals die kaart het formuleerde.
Dat is een probleem, want 7.2.3.1 zegt met zoveel woorden dat kolom 16b
vóórgaat op de scheidingstabel van 7.2.4: juist die kolom moet volledig zijn.

Deze module leest de lijst zelf — 2860 vermeldingen, uitgelezen door
scripts/extract_imdg_dgl.py uit de tekst van resolutie MSC.556(108) — en geeft
per UN-nummer terug wat er in de kolommen staat. Vermeldingen met meerdere
verpakkingsgroepen (UN 1361, UN 3424 en zo'n vijfhonderd andere) staan meerdere
keren in de lijst; die worden hier op verpakkingsgroep uit elkaar gehouden.

De bron zet een streepje waar niets geldt. Dat is opmaak en geen gegeven, dus
het wordt hier weggelaten in plaats van als waarde doorgegeven.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

_SEED = Path(__file__).resolve().parents[3] / "seed" / "dg" / "imdg_dgl.json"
_lock = threading.Lock()
_index: dict[str, list[dict[str, Any]]] | None = None
_meta: dict[str, Any] = {}

# Het en-streepje van de uitgave, en de gewone koppelteken-variant.
_EMPTY = {"-", "–", "—", ""}

# "Category 03 SW1", "Category B SW2 SW5", "– SW1 SW22", "Category A"
_CATEGORY = re.compile(r"Category\s+(\S+)")
_CODE = re.compile(r"\b(SW\d{1,2}|H\d|SG\d{1,2}|SGG\d{1,2}[a-z]?)\b")


def _load() -> dict[str, list[dict[str, Any]]]:
    global _index
    with _lock:
        if _index is None:
            index: dict[str, list[dict[str, Any]]] = {}
            try:
                raw = json.loads(_SEED.read_text(encoding="utf-8"))
            except (OSError, ValueError):  # pragma: no cover - seed ontbreekt
                raw = {}
            for entry in raw.get("entries", []):
                index.setdefault(str(entry.get("un_number", "")), []).append(entry)
            _meta.update({
                "amendment": raw.get("amendment", ""),
                "source": raw.get("source", ""),
                "entries": len(raw.get("entries", [])),
            })
            _index = index
    return _index


def available() -> bool:
    """Of de lijst geladen kon worden. Zonder lijst blijft de app werken."""
    return bool(_load())


def source() -> dict[str, Any]:
    _load()
    return dict(_meta)


def _digits(un_number: str) -> str:
    return "".join(ch for ch in str(un_number or "") if ch.isdigit()).zfill(4)


def entries_for(un_number: str) -> list[dict[str, Any]]:
    """Alle rijen van de lijst voor dit UN-nummer, op volgorde van de lijst."""
    return list(_load().get(_digits(un_number), []))


def entry_for(un_number: str, packing_group: str = "") -> dict[str, Any]:
    """De rij die bij deze stof en verpakkingsgroep hoort.

    Zonder opgegeven verpakkingsgroep, of als die niet voorkomt, wordt de
    eerste rij teruggegeven: de kolommen die de app gebruikt — scheiding,
    stuwage, EmS — verschillen tussen de verpakkingsgroepen van één stof
    zelden, en een rij van de goede stof is beter dan geen rij.
    """
    rows = entries_for(un_number)
    if not rows:
        return {}
    wanted = str(packing_group or "").strip().upper()
    if wanted:
        for row in rows:
            if str(row.get("packing_group", "")).strip().upper() == wanted:
                return dict(row)
    return dict(rows[0])


def value(entry: dict[str, Any], column: str) -> str:
    """De waarde van een kolom, of leeg waar de lijst een streepje zet."""
    text = str(entry.get(column) or "").strip()
    return "" if text in _EMPTY else text


def codes(entry: dict[str, Any], column: str) -> list[str]:
    """De codes uit een kolom, ontdubbeld en op volgorde van de lijst.

    Kolom 16a draagt naast de codes ook de stuwagecategorie ("Category B
    SW2 SW5"); die wordt hier niet als code meegeteld. Kolom 16b draagt naast
    de SG-codes de scheidingsgroepen van de stof ("SGG2 SG27 SG31").
    """
    found: list[str] = []
    for match in _CODE.finditer(value(entry, column)):
        code = match.group(1).upper()
        if code not in found:
            found.append(code)
    return found


def stowage_category(entry: dict[str, Any]) -> str:
    """De stuwagecategorie uit kolom 16a: A t/m E, of 01 t/m 05 voor klasse 1."""
    match = _CATEGORY.search(value(entry, "stowage_and_handling"))
    return match.group(1) if match else ""


def stowage_codes(entry: dict[str, Any]) -> list[str]:
    """De SW- en H-codes uit kolom 16a."""
    return [c for c in codes(entry, "stowage_and_handling") if not c.startswith("SG")]


def segregation_codes(entry: dict[str, Any]) -> list[str]:
    """De SG-codes uit kolom 16b, zonder de scheidingsgroepen."""
    return [c for c in codes(entry, "segregation") if not c.startswith("SGG")]


def segregation_groups(entry: dict[str, Any]) -> list[str]:
    """De SGG-codes uit kolom 16b."""
    return [c for c in codes(entry, "segregation") if c.startswith("SGG")]


def special_provisions(entry: dict[str, Any]) -> list[str]:
    """De nummers uit kolom 6, bijvoorbeeld ['223', '274']."""
    return re.findall(r"\d+", value(entry, "special_provisions"))


def amended_in_42_24(entry: dict[str, Any]) -> bool:
    """Of de lijst deze vermelding met het wijzigingsdriehoekje aanwijst."""
    return bool(entry.get("amended"))
