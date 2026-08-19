"""The IMDG card, from the Amendment 42-24 Dangerous Goods List reading.

The row comes verbatim from ``backend/seed/dg/imdg_dgl.json`` — the DGL of
chapter 3.2 of IMDG Code Amendment 42-24 as adopted by IMO resolution
MSC.556(108) — including the columns the sea code has and the land codes do
not: EmS, stowage and handling, segregation, and the properties and
observations column. Concepts of the land regulations (tunnel codes,
transport categories, orange plates) do not exist in the IMDG Code and are
not printed.
"""
from __future__ import annotations

import json
from functools import lru_cache

from .base import SEED, CardPage, SourceUnavailable, dash


@lru_cache(maxsize=1)
def _table() -> dict:
    return json.loads((SEED / "imdg_dgl.json").read_text(encoding="utf-8"))


def _clean(value: str | None) -> str:
    """The DGL prints an en dash for an empty cell; keep one dash style."""
    value = (value or "").strip()
    return "" if value in {"–", "-", "—"} else value


def cards(un: str) -> list[CardPage]:
    rows = [e for e in _table()["entries"] if e.get("un_number") == un]
    if not rows:
        raise SourceUnavailable(
            f"UN {un} has no row in the IMDG 42-24 Dangerous Goods List reading "
            "(backend/seed/dg/imdg_dgl.json)")

    amendment = _table().get("amendment") or "IMDG Code Amendment 42-24"
    pages: list[CardPage] = []
    for row in rows:
        name = (row.get("proper_shipping_name") or "").strip()
        subsidiary = _clean(row.get("subsidiary_hazards"))
        # Column (4) separates several subsidiary hazards with a slash and
        # appends "P" when the substance is a marine pollutant: "5.1/8 P".
        pollutant = False
        subsidiary_codes: list[str] = []
        for token in subsidiary.replace(",", "/").split("/"):
            token = token.strip()
            if token.endswith(" P"):
                token = token[:-2].strip()
                pollutant = True
            if token == "P":
                pollutant = True
                continue
            if token:
                subsidiary_codes.append(token)
        labels = [str(row.get("class") or "").strip()] if row.get("class") else []
        labels += subsidiary_codes
        if pollutant:
            labels.append("MP")

        packing = _clean(row.get("packing_instructions"))
        packing_provisions = _clean(row.get("packing_provisions"))
        ibc = _clean(row.get("ibc_instructions"))
        ibc_provisions = _clean(row.get("ibc_provisions"))
        packaging_rows: list[tuple[str, str]] = [(
            "Packaging",
            (f"Permitted in packagings in accordance with packing instruction {packing}"
             + (f", provisions {packing_provisions}" if packing_provisions else "")
             + " — see IMDG 4.1.4.") if packing
            else "No packing instruction is assigned in column (8).")]
        if ibc:
            packaging_rows.append((
                "IBCs",
                f"Instruction {ibc}"
                + (f", provisions {ibc_provisions}" if ibc_provisions else "")
                + " — see IMDG 4.1.4.2."))
        properties = _clean(row.get("properties_and_observations"))
        if properties:
            packaging_rows.append(("Properties and observations", properties))

        tank = _clean(row.get("tank_instructions"))
        tank_provisions = _clean(row.get("tank_provisions"))
        imo_tank = _clean(row.get("imo_tank_instructions"))

        provision_rows: list[tuple[str, str]] = []
        special = _clean(row.get("special_provisions"))
        if special:
            provision_rows.append(("Special provisions", f"{special} — see IMDG 3.3"))
        stowage = _clean(row.get("stowage_and_handling"))
        if stowage:
            provision_rows.append(("Stowage and handling", f"{stowage} — see IMDG 7.1"))
        segregation = _clean(row.get("segregation"))
        if segregation:
            provision_rows.append(("Segregation", f"{segregation} — see IMDG 7.2"))
        if not provision_rows:
            provision_rows.append(
                ("Special provisions",
                 "No special provisions are assigned to this entry in the DGL."))

        pages.append(CardPage(
            modality="IMDG",
            un=un,
            names={"en": name},
            klass=dash(row.get("class")),
            packing_group=_clean(row.get("packing_group")) or "Not applicable",
            classification_code="Not applicable",
            labels=labels,
            identity_extra=[
                ("Subsidiary hazards", ", ".join(subsidiary_codes) or "—"),
                ("Marine pollutant", "Yes (P)" if pollutant else "No"),
                ("EmS", _clean(row.get("ems")) or "—"),
            ],
            label_extra=[],
            marking=f"UN {un} {name}".strip(),
            packaging_rows=packaging_rows,
            tank_rows=[
                ("Portable tank instructions", tank or "—"),
                ("Tank special provisions", tank_provisions or "—"),
                ("IMO tank instructions", imo_tank or "—"),
            ],
            provision_rows=provision_rows,
            lq_eq=(
                _clean(row.get("limited_quantity")) or "—",
                _clean(row.get("excepted_quantity")) or "—",
            ),
            regulation=amendment,
            source=_table().get("source", ""),
        ))
    return pages
