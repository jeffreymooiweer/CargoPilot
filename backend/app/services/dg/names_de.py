"""The German proper shipping names from ADR table A, 2025 edition.

The application has always had German names — ``un_numbers.json`` carries them —
but from a **2023** export, and the manifest has carried that as an erratum
since v1.56.0. It stood because UNECE publishes the ADR in English and French
only, and there was no German edition to read. There is one: the national
edition of the Bundesamt für Strassen, supplied by the operator and registered
as ``adr_de_1``.

``scripts/extract_adr_names_multilingual.py`` reads column (2) out of it and
writes ``seed/dg/adr_names_de.json`` above an agreement gate against the UN
numbers of the Dutch table A. This module makes the result available per UN
number, and it takes precedence over the 2023 name: same language, newer
edition.

One UN number can carry several names on separate rows; the German edition
joins such alternatives with "oder", and so does this.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

_SEED = Path(__file__).resolve().parents[3] / "seed" / "dg" / "adr_names_de.json"

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
    """Which ADR edition the German names were read from."""
    _load()
    return _edition


def german_names(un_number: str) -> list[str]:
    """Every name table A gives this UN number, in the order it gives them."""
    digits = "".join(ch for ch in str(un_number) if ch.isdigit()).zfill(4)
    return list(_load().get(digits, ()))


def german_name(un_number: str) -> str:
    """The German proper shipping name, alternatives joined with "oder"."""
    return " oder ".join(german_names(un_number))
