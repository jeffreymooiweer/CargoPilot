"""The RID card, from the RID 2025 table A reading in this repository.

The row comes from ``backend/seed/dg/rid_table_a.json`` — RID 3.2.1 read
from three independently typeset editions (Dutch and OTIF English as the
two readings, the OTIF German arbitrating the cells where they disagreed).
The rail table has columns the road table does not print: the RID tank
code and its TE/TU provisions, the wagon/container provisions W (7.2.4),
the bulk provisions VC/AP (7.3), the loading provisions CW (7.5.11), the
express parcels CE (7.6) — and the shunting models 13/15 of 5.3.4 stand
bracketed in the labels column. Road concepts (tunnel codes, orange-plate
1.1.3.6 points) do not exist here and are not printed.

A row the RID prints as CARRIAGE PROHIBITED or NOT SUBJECT TO RID becomes
a card saying exactly that — a rail consignor is better served by the
prohibition than by silence.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from .base import SEED, CardPage, SourceUnavailable, dash


@lru_cache(maxsize=1)
def _table() -> dict:
    return json.loads((SEED / "rid_table_a.json").read_text(encoding="utf-8"))


_IDENTITY_FIELDS = (
    "class", "classification_code", "packing_group", "labels",
    "special_provisions", "limited_quantity", "excepted_quantity",
    "packing_instructions", "packing_provisions", "mixed_packing_provisions",
    "portable_tank_instructions", "portable_tank_provisions", "tank_code",
    "tank_provisions", "transport_category", "packages_provisions",
    "bulk_provisions", "loading_provisions", "express_parcels",
    "hazard_number", "carriage_prohibited", "not_subject",
)


def _unique(rows: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    kept: list[dict] = []
    for row in rows:
        key = tuple(str(row.get(field) or "").strip() for field in _IDENTITY_FIELDS)
        if key not in seen:
            seen.add(key)
            kept.append(row)
    return kept


def _shunting(labels: str) -> str:
    """The bracketed shunting models of column (5), as 5.3.4 assigns them."""
    models = re.findall(r"\(\+(1[35])\)", labels or "")
    if not models:
        return "None assigned in column (5)."
    return ("Model(s) " + " and ".join(sorted(set(models)))
            + " — shunting labels of RID 5.3.4, affixed as its conditions require.")


def cards(un: str) -> list[CardPage]:
    rows = _unique([e for e in _table()["entries"] if e.get("un") == un])
    if not rows:
        raise SourceUnavailable(
            f"UN {un} has no row in the RID 2025 table A reading "
            "(backend/seed/dg/rid_table_a.json)")

    edition = _table().get("edition", "RID")
    pages: list[CardPage] = []
    for row in rows:
        names = {}
        if (row.get("name_en") or "").strip():
            names["en"] = row["name_en"].strip()
        if (row.get("name_nl") or "").strip():
            names["nl"] = row["name_nl"].strip()
        name_for_marking = names.get("en") or names.get("nl") or ""

        if row.get("carriage_prohibited") or row.get("not_subject"):
            notice = ("CARRIAGE PROHIBITED — RID table A strikes this entry "
                      "for rail." if row.get("carriage_prohibited") else
                      "NOT SUBJECT TO RID — table A releases this entry "
                      "from the RID's provisions.")
            pages.append(CardPage(
                modality="RID", un=un,
                names=names or {"en": ""},
                klass=dash(row.get("class")),
                packing_group=(row.get("packing_group") or "").strip() or "Not applicable",
                classification_code=dash(row.get("classification_code")),
                labels=[],
                identity_extra=[("Rail status", notice)],
                label_extra=[],
                marking=f"UN {un} {name_for_marking}".strip(),
                packaging_rows=[("Carriage by rail", notice)],
                tank_rows=[],
                provision_rows=[("Rail status", notice)],
                lq_eq=("—", "—"),
                regulation=edition,
                source=_table().get("source", ""),
            ))
            continue

        labels = [p.strip() for p in re.sub(r"\(\+1[35]\)", "", row.get("labels") or "")
                  .replace("+", ",").split(",") if p.strip()]

        packing = (row.get("packing_instructions") or "").strip()
        packing_provisions = (row.get("packing_provisions") or "").strip()
        mixed = (row.get("mixed_packing_provisions") or "").strip()
        packaging_rows: list[tuple[str, str]] = [(
            "Packaging",
            (f"Permitted in packagings in accordance with packing "
             f"instruction {packing}"
             + (f", special packing provisions {packing_provisions}" if packing_provisions else "")
             + " — see RID 4.1.4.") if packing
            else "No packing instruction is assigned in column (8).")]
        if mixed:
            packaging_rows.append(
                ("Mixed packing", f"{mixed} — see RID 4.1.10."))

        provision_rows: list[tuple[str, str]] = []
        if (row.get("special_provisions") or "").strip():
            provision_rows.append(
                ("Special provisions",
                 f"{row['special_provisions']} — see RID 3.3"))
        if (row.get("packages_provisions") or "").strip():
            provision_rows.append(
                ("Packages (wagons and containers)",
                 f"{row['packages_provisions']} — see RID 7.2.4"))
        if (row.get("bulk_provisions") or "").strip():
            provision_rows.append(
                ("Carriage in bulk",
                 f"{row['bulk_provisions']} — see RID 7.3"))
        if (row.get("loading_provisions") or "").strip():
            provision_rows.append(
                ("Loading, unloading and handling",
                 f"{row['loading_provisions']} — see RID 7.5.11"))
        if (row.get("express_parcels") or "").strip():
            provision_rows.append(
                ("Express parcels",
                 f"{row['express_parcels']} — see RID 7.6"))
        if not provision_rows:
            provision_rows.append(
                ("Special provisions",
                 "No special provisions are assigned to this entry in table A."))

        pages.append(CardPage(
            modality="RID",
            un=un,
            names=names or {"en": ""},
            klass=dash(row.get("class")),
            packing_group=(row.get("packing_group") or "").strip() or "Not applicable",
            classification_code=dash(row.get("classification_code")),
            labels=labels,
            identity_extra=[
                ("Transport category", dash(row.get("transport_category"))),
                ("Hazard identification number", dash(row.get("hazard_number"))),
            ],
            label_extra=[
                ("Shunting labels (5.3.4)", _shunting(row.get("labels") or "")),
            ],
            marking=f"UN {un} {name_for_marking}".strip(),
            packaging_rows=packaging_rows,
            tank_rows=[
                ("RID tank code (4.3)", dash(row.get("tank_code"))),
                ("Tank special provisions (TU/TE)", dash(row.get("tank_provisions"))),
                ("Portable tank instructions", dash(row.get("portable_tank_instructions"))),
                ("Portable tank provisions", dash(row.get("portable_tank_provisions"))),
            ],
            provision_rows=provision_rows,
            lq_eq=(
                (row.get("limited_quantity") or "").strip() or "—",
                (row.get("excepted_quantity") or "").strip() or "—",
            ),
            regulation=edition,
            source=_table().get("source", ""),
        ))
    return pages


def available_un_numbers() -> list[str]:
    """Every UN number the measured RID table assigns at least one row."""
    return sorted({e["un"] for e in _table()["entries"] if e.get("un")})
