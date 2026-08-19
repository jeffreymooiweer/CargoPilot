"""ICAO: honestly unavailable — this repository holds no air table at all.

The ICAO Technical Instructions are sold by ICAO and the IATA DGR table 4.2
is commercial content; neither is in this repository's regulations store,
and no free official full-table source has been adopted. Until one is (with
licence terms that permit machine reading), an ICAO card cannot be generated
without inventing data — so the generation fails aloud instead.
"""
from __future__ import annotations

from .base import CardPage, SourceUnavailable


def cards(un: str) -> list[CardPage]:
    raise SourceUnavailable(
        "No measured ICAO/air table exists in this repository: the ICAO "
        "Technical Instructions and the IATA DGR are not freely licensable "
        "sources. An air card requires adopting a licensed or official open "
        "source first; nothing is generated rather than something invented.")


def available_un_numbers() -> list[str]:
    """No air table exists in this repository, so no UN number is offered."""
    return []
