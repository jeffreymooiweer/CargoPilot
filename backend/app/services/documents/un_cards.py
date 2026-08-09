"""The UN cards that belong to a shipment.

`un_cards/` holds one PDF per UN number, named `un_1203.pdf`. They are fetched
once by the **Fetch UN cards** workflow, which reads the UN number out of each
document rather than trusting its original filename.

A shipment only ever needs the handful of cards for the substances the user
actually declared, so the export bundles exactly those into a zip. If the folder
is absent — a fork that did not run the workflow — the feature simply reports
that no cards are available, rather than breaking the export.
"""
from __future__ import annotations

import io
import os
import re
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any

CARD_PATTERN = re.compile(r"^un_(\d{4})(?:-(\d+))?\.pdf$", re.IGNORECASE)


def cards_dir() -> Path:
    """Where the cards live: `un_cards/` at the repository or image root."""
    override = os.environ.get("UN_CARDS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / "un_cards"


@lru_cache(maxsize=1)
def _index() -> dict[str, list[Path]]:
    """UN number → the card files for it, in filename order.

    A UN number can have more than one card; the fetcher names the extras
    `un_1203-2.pdf`. All of them are handed to the user — deciding which variant
    applies is not something this app should guess at.
    """
    directory = cards_dir()
    found: dict[str, list[Path]] = {}
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("un_*.pdf")):
        match = CARD_PATTERN.match(path.name)
        if match:
            found.setdefault(match.group(1), []).append(path)
    return found


def reset_cache() -> None:
    """Forget the scan of the folder — used by the tests."""
    _index.cache_clear()


def has_un_cards() -> bool:
    return bool(_index())


def card_count() -> int:
    """How many UN numbers have at least one card."""
    return len(_index())


def un_numbers_in(dangerous_goods: list[dict[str, Any]] | None) -> list[str]:
    """The UN numbers the user declared, in order, without duplicates."""
    seen: list[str] = []
    for entry in dangerous_goods or []:
        for product in entry.get("products") or []:
            raw = str(product.get("un_number") or "").strip()
            digits = re.sub(r"\D", "", raw)
            if len(digits) == 4 and digits not in seen:
                seen.append(digits)
    return seen


def availability(dangerous_goods: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Which of the shipment's UN numbers we hold a card for."""
    index = _index()
    requested = un_numbers_in(dangerous_goods)
    available = [un for un in requested if un in index]
    return {
        "enabled": bool(index),
        "requested": requested,
        "available": available,
        "missing": [un for un in requested if un not in index],
        "count": len(available),
    }


def build_zip(dangerous_goods: list[dict[str, Any]] | None) -> tuple[Path, dict[str, Any]]:
    """Bundle the cards for this shipment. Raises FileNotFoundError if there are none."""
    index = _index()
    status = availability(dangerous_goods)
    if not status["available"]:
        raise FileNotFoundError("no UN cards available for this shipment")

    fd, name = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    out_path = Path(name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass

    readme = io.StringIO()
    readme.write(
        "UN cards for this shipment\n"
        "==========================\n\n"
        "One card per UN number you declared. These are reference documents from a\n"
        "third party, included unchanged for your own records. They are not part of\n"
        "the transport documentation and do not replace the current edition of ADR,\n"
        "RID, ADN, the IMDG Code or the IATA DGR.\n\n"
    )
    for un in status["available"]:
        readme.write(f"  UN {un}  ->  {', '.join(p.name for p in index[un])}\n")
    if status["missing"]:
        readme.write(
            "\nNo card is held for the following UN numbers:\n"
            + "".join(f"  UN {un}\n" for un in status["missing"])
        )

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for un in status["available"]:
            for path in index[un]:
                archive.write(path, arcname=path.name)
        archive.writestr("README.txt", readme.getvalue())

    return out_path, status
