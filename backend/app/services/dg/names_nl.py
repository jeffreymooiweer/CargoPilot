"""The Dutch proper shipping names from ADR table A.

The Table A export the UN database was built on carries two name columns,
``name_en`` and ``name_de``. From that the app concluded — in four places, in so
many words — that the ADR has no Dutch name. It has. The ADR appears in an
official Dutch edition and column (2) there reads BENZINE, ZOUTZUUR,
LITHIUM-ION-BATTERIJEN; only the export did not carry it.

``scripts/extract_adr_names.py`` reads that column out of the Dutch edition and
writes ``seed/dg/adr_names_nl.json``. This module makes it available per UN
number.

**One UN number can have several names.** Table A gives UN 1203 as BENZINE and
as MOTORBRANDSTOF, on separate rows, and the same for 144 other numbers. That is
the same thing the English column does with its "or": "Ethanol or Ethyl alcohol
or Ethanol solutions". So they are joined the same way, with the Dutch "of".
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

_SEED = Path(__file__).resolve().parents[3] / "seed" / "dg" / "adr_names_nl.json"

_lock = threading.Lock()
_cache: dict[str, list[str]] | None = None
_edition: str = ""


def _load() -> dict[str, list[str]]:
    global _cache, _edition
    with _lock:
        if _cache is None:
            try:
                payload = json.loads(_SEED.read_text(encoding="utf-8"))
            except (OSError, ValueError):  # pragma: no cover - seed missing
                payload = {}
            _edition = str(payload.get("edition") or "")
            _cache = {
                str(un): [str(name) for name in names if str(name).strip()]
                for un, names in (payload.get("names") or {}).items()
            }
    return _cache


def edition() -> str:
    """Which ADR edition the Dutch names were read from."""
    _load()
    return _edition


def dutch_names(un_number: str) -> list[str]:
    """Every name table A gives this UN number, in the order it gives them."""
    digits = "".join(ch for ch in str(un_number) if ch.isdigit()).zfill(4)
    return list(_load().get(digits, ()))


def dutch_name(un_number: str) -> str:
    """The Dutch proper shipping name, alternatives joined with "of"."""
    return " of ".join(dutch_names(un_number))
