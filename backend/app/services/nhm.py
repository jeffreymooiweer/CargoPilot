"""The NHM goods nomenclature for box 24 of the CIM, searchable.

The NHM (Nomenclature Harmonisée Marchandises) is the UIC's goods
nomenclature for rail; the CIM consignment note asks for it in box 24 in six
digits, and those six digits are the Harmonized System subheading. Until
v1.183.0 the box was free text with a format check and a note that the code
had to be looked up elsewhere — true, but not an answer.

The seed ``backend/seed/nhm.json`` is built by ``scripts/build_nhm_seed.py``
from the UIC's own correspondence table "NST 2007 – NHM 2025", which carries
every NHM 2025 position with its English and French label and the NST 2007
group it maps to. 5,640 six-digit codes: 5,612 Harmonized System subheadings
and 28 railway-specific positions of chapter 99 (groupage freight, empty
wagons, loaded intermodal units). Labels exist in English and French only,
because that is what the UIC publishes; the interface says so.

Searching is by code prefix — a person who knows "7208" gets the 7208
subheadings — or by word in either label, the way the location search
works. Loaded once, kept in memory; no database.
"""
from __future__ import annotations

import json
import re
import threading
import unicodedata
from typing import Any

from app.core.config import get_settings

_lock = threading.Lock()
_entries: list[dict[str, Any]] | None = None
_by_code: dict[str, dict[str, Any]] = {}


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def _load() -> list[dict[str, Any]]:
    global _entries
    with _lock:
        if _entries is None:
            path = get_settings().seed_dir / "nhm.json"
            entries = json.loads(path.read_text(encoding="utf-8"))
            for entry in entries:
                entry["_words"] = _fold(f"{entry['en']} {entry['fr']}")
                _by_code[entry["code"]] = entry
            _entries = entries
    return _entries


def _public(entry: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def nhm_entry(code: str) -> dict[str, Any] | None:
    """The one entry a six-digit code names, or nothing."""
    _load()
    entry = _by_code.get(re.sub(r"\D", "", str(code or "")))
    return _public(entry) if entry else None


def nhm_count() -> int:
    return len(_load())


def search_nhm(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Codes by prefix, or labels by word — the best first.

    A query of digits (spaces allowed, as the table prints "7208 51") is a
    code prefix. Anything else is matched on the words of the English and
    French labels: a label whose word starts with the query outranks one
    that merely contains it, and shorter labels outrank longer ones among
    equals, because the shorter one is the heading the person meant.
    """
    raw = str(query or "").strip()
    digits = re.sub(r"\s", "", raw)
    if not raw:
        return []
    entries = _load()
    scored: list[tuple[int, int, dict[str, Any]]] = []
    if digits.isdigit():
        for entry in entries:
            if entry["code"].startswith(digits):
                scored.append((0, 0, entry))
    else:
        needle = _fold(raw)
        if len(needle) < 2:
            return []
        word_start = re.compile(rf"(?<![a-z0-9]){re.escape(needle)}")
        for entry in entries:
            words = entry["_words"]
            if word_start.search(words):
                scored.append((0, len(entry["en"]), entry))
            elif needle in words:
                scored.append((1, len(entry["en"]), entry))
    scored.sort(key=lambda item: (item[0], item[1], item[2]["code"]))
    return [_public(entry) for _, _, entry in scored[:limit]]
