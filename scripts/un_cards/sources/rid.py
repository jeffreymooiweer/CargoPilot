"""RID: honestly unavailable until the RID table A is read per column.

This repository holds the RID 2025 editions in its regulations store and has
read *one* column of its table A per substance — the bracketed shunting
models of column (5), extracted and cross-checked between the English and
German editions in v1.123.0. One column is not a card. The remaining columns
(RID's own carriage, loading and express-parcel provisions among them) must
be extracted from the RID editions the same measured way before a RID card
can be generated; borrowing the ADR row and relabelling it "RID" would put
road-only claims on a rail card.
"""
from __future__ import annotations

from .base import CardPage, SourceUnavailable


def cards(un: str) -> list[CardPage]:
    raise SourceUnavailable(
        "The RID table A has not been column-read yet: only column (5) "
        "(shunting models, v1.123.0) is extracted. Generating a RID card from "
        "the ADR row would relabel road data as rail data. Needed: a "
        "geometric extraction of RID 3.2.1 from the RID 2025 editions in the "
        "regulations store, like scripts/extract_rid_shunting_labels.py did "
        "for column (5).")


def available_un_numbers() -> list[str]:
    """No RID card can be generated yet, so no UN number is offered."""
    return []
