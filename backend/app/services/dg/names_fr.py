"""The French proper shipping names from ADR table A.

The ADR is authentic in English **and in French**, and column (2) of table A is
printed in both. Until v1.75.0 a French reader of this application was handed
the English name, on the reasoning that French is one of the three languages
5.4.1.4.1 allows to stand alone anyway — true, and still second best: the name
the French edition prints is the name a French-speaking authority expects to
read, and "ESSENCE" is not a translation of GASOLINE but its equal.

``scripts/extract_adr_names_multilingual.py`` reads the column out of the
official UNECE French volume (register id ``adr1_fr``) and writes
``seed/dg/adr_names_fr.json``, above an agreement gate against the UN numbers
of the Dutch table A. This module makes the result available per UN number.

As in the Dutch edition, one UN number can carry several names on separate
rows; the French edition joins such alternatives with "ou", and so does this.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

_SEED = Path(__file__).resolve().parents[3] / "seed" / "dg" / "adr_names_fr.json"

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
    """Which ADR edition the French names were read from."""
    _load()
    return _edition


def french_names(un_number: str) -> list[str]:
    """Every name table A gives this UN number, in the order it gives them."""
    digits = "".join(ch for ch in str(un_number) if ch.isdigit()).zfill(4)
    return list(_load().get(digits, ()))


def french_name(un_number: str) -> str:
    """The French proper shipping name, alternatives joined with "ou"."""
    return " ou ".join(french_names(un_number))
