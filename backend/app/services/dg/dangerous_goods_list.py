"""The Dangerous Goods List of IMDG Code Amendment 42-24, per UN number.

Until now the app knew columns 16a and 16b only for the substances that happened
to have a UN card, and then only as that card worded it. That is a problem,
because 7.2.3.1 says in so many words that column 16b prevails over the
segregation table of 7.2.4: that column of all columns has to be complete.

This module reads the list itself — 2860 entries, extracted by
scripts/extract_imdg_dgl.py from the text of resolution MSC.556(108) — and
returns per UN number what is in the columns. Entries with several packing
groups (UN 1361, UN 3424 and some five hundred others) appear in the list more
than once; those are kept apart here by packing group.

The source puts a dash where nothing applies. That is formatting and not data,
so it is dropped here instead of being passed on as a value.
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

# The publication's en dash, and the ordinary hyphen variant.
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
    """Whether the list could be loaded. Without it the app keeps working."""
    return bool(_load())


def source() -> dict[str, Any]:
    _load()
    return dict(_meta)


def _digits(un_number: str) -> str:
    return "".join(ch for ch in str(un_number or "") if ch.isdigit()).zfill(4)


def entries_for(un_number: str) -> list[dict[str, Any]]:
    """Every row of the list for this UN number, in the order of the list."""
    return list(_load().get(_digits(un_number), []))


def entry_for(un_number: str, packing_group: str = "") -> dict[str, Any]:
    """The row belonging to this substance and packing group.

    Without a packing group given, or when it does not occur, the first row is
    returned: the columns the app uses — segregation, stowage, EmS — rarely
    differ between the packing groups of one substance, and a row of the right
    substance is better than no row.
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
    """The value of a column, or empty where the list puts a dash."""
    text = str(entry.get(column) or "").strip()
    return "" if text in _EMPTY else text


def codes(entry: dict[str, Any], column: str) -> list[str]:
    """The codes from a column, deduplicated and in the order of the list.

    Besides the codes, column 16a also carries the stowage category ("Category B
    SW2 SW5"); that is not counted as a code here. Besides the SG codes, column
    16b carries the substance's segregation groups ("SGG2 SG27 SG31").
    """
    found: list[str] = []
    for match in _CODE.finditer(value(entry, column)):
        code = match.group(1).upper()
        if code not in found:
            found.append(code)
    return found


def stowage_category(entry: dict[str, Any]) -> str:
    """The stowage category from column 16a: A to E, or 01 to 05 for class 1."""
    match = _CATEGORY.search(value(entry, "stowage_and_handling"))
    return match.group(1) if match else ""


def stowage_codes(entry: dict[str, Any]) -> list[str]:
    """The SW and H codes from column 16a."""
    return [c for c in codes(entry, "stowage_and_handling") if not c.startswith("SG")]


def segregation_codes(entry: dict[str, Any]) -> list[str]:
    """The SG codes from column 16b, without the segregation groups."""
    return [c for c in codes(entry, "segregation") if not c.startswith("SGG")]


def segregation_groups(entry: dict[str, Any]) -> list[str]:
    """The SGG codes from column 16b."""
    return [c for c in codes(entry, "segregation") if c.startswith("SGG")]


def special_provisions(entry: dict[str, Any]) -> list[str]:
    """The numbers from column 6, for example ['223', '274']."""
    return re.findall(r"\d+", value(entry, "special_provisions"))


def amended_in_42_24(entry: dict[str, Any]) -> bool:
    """Whether the list marks this entry with the amendment triangle."""
    return bool(entry.get("amended"))
