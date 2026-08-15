"""The English proper shipping names from ADR table A, out of the 2025 edition.

English was the last of the four still coming from an export of ADR **2023**.
That export was reduced to one job in v1.56.0 — the foreign names the Dutch
edition has no column for — and by v1.79.0 German had moved to the 2025 book
and by v1.75.0 French had, leaving English alone on it. Which is the wrong one
to leave: 5.4.1.4.1 lets French, German and English each stand on their own, so
a Dutch or German consignor sees their own name, but the language that goes
*beside* the Dutch one on almost every document this application produces is
the English one, and at sea and in the air it is the only one permitted
(IMDG 5.4.1.4.1, IATA DGR 8.1.2.1).

What the export cost, measured rather than remembered: fourteen entries carry
no English name at all in it and UN 1139 carries the truncated "Coating
solution (" — both are read whole from the 2025 volume. Alternatives are joined
with "or", as that edition sets them.

``scripts/extract_adr_names_multilingual.py`` reads column (2) out of the
official UNECE English volume (register id ``adr1``) and writes
``seed/dg/adr_names_en.json`` above an agreement gate against the UN numbers of
the Dutch table A.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

_SEED = Path(__file__).resolve().parents[3] / "seed" / "dg" / "adr_names_en.json"

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
    """Which ADR edition the English names were read from."""
    _load()
    return _edition


def english_names(un_number: str) -> list[str]:
    """Every name table A gives this UN number, in the order it gives them."""
    digits = "".join(ch for ch in str(un_number) if ch.isdigit()).zfill(4)
    return list(_load().get(digits, ()))


def english_name(un_number: str) -> str:
    """The English proper shipping name, alternatives joined with "or"."""
    return " or ".join(english_names(un_number))
