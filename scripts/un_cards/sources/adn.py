"""The ADN card, from the ADN 2025 table A reading in this repository.

Rail-and-road concepts (transport category, tunnel code, orange plates on a
vehicle) do not exist on the waterway and are not printed here. What the ADN
column set actually assigns — whether carriage is permitted and in what,
the equipment required on board (PP, EX, A…), ventilation, measures during
loading, and the number of blue cones or lights of 7.1.5 — comes verbatim
from ``backend/seed/dg/adn_table_a.json``. Names come from the ADR name
registers, which is the UN model's own name set; the ADN prints the same
proper shipping names.
"""
from __future__ import annotations

import json
from functools import lru_cache

from .base import SEED, CardPage, SourceUnavailable, dash
from .adr import _names


@lru_cache(maxsize=1)
def _table() -> dict:
    return json.loads((SEED / "adn_table_a.json").read_text(encoding="utf-8"))


#: See ``adr.unique_rows``: the printed table repeats rows per alternative
#: name; only regulatory content warrants a second card page.
_IDENTITY_FIELDS = (
    "class", "classification_code", "packing_group", "labels",
    "special_provisions", "limited_quantity", "carriage_permitted",
    "equipment", "ventilation", "loading_measures", "blue_cones", "remarks",
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


def cards(un: str) -> list[CardPage]:
    rows = _unique([e for e in _table()["entries"] if e.get("un") == un])
    if not rows:
        raise SourceUnavailable(
            f"UN {un} has no row in the ADN 2025 table A reading "
            "(backend/seed/dg/adn_table_a.json)")

    names = {}
    for language in ("en", "nl"):
        found = _names(language).get(un) or []
        if found:
            names[language] = " / ".join(found)

    edition = _table().get("edition", "ADN")
    pages: list[CardPage] = []
    for row in rows:
        labels = [p.strip() for p in (row.get("labels") or "").split(",") if p.strip()]
        cones = row.get("blue_cones")
        carriage = (row.get("carriage_permitted") or "").strip()
        if carriage == "T":
            carriage_text = "Permitted in tank vessels (T) — see ADN 3.2.1, column (8)."
        elif carriage == "B":
            carriage_text = "Permitted in bulk (B) — see ADN 3.2.1, column (8)."
        elif carriage:
            carriage_text = f"{carriage} — see ADN 3.2.1, column (8)."
        else:
            carriage_text = "In packages; column (8) assigns no tank or bulk code."

        provision_rows: list[tuple[str, str]] = []
        if (row.get("special_provisions") or "").strip():
            provision_rows.append(
                ("Special provisions", f"{row['special_provisions']} — see ADN 3.3"))
        if (row.get("loading_measures") or "").strip():
            provision_rows.append(
                ("Loading, unloading and carriage",
                 f"{row['loading_measures']} — see ADN 7.1.6"))
        if (row.get("remarks") or "").strip():
            provision_rows.append(("Remarks", row["remarks"]))
        if not provision_rows:
            provision_rows.append(
                ("Special provisions",
                 "No special provisions are assigned to this entry in table A."))

        name_for_marking = names.get("en") or row.get("name_nl") or ""
        pages.append(CardPage(
            modality="ADN",
            un=un,
            names=names or {"nl": row.get("name_nl") or ""},
            klass=dash(row.get("class")),
            packing_group=(row.get("packing_group") or "").strip() or "Not applicable",
            classification_code=dash(row.get("classification_code")),
            labels=labels,
            identity_extra=[
                ("Carriage permitted", carriage or "Packages"),
            ],
            label_extra=[
                ("Blue cones / lights (7.1.5)",
                 str(cones) if cones is not None else "—"),
            ],
            marking=f"UN {un} {name_for_marking}".strip(),
            packaging_rows=[
                ("Carriage", carriage_text),
            ],
            tank_rows=[
                ("Equipment required (8.1.5)", dash(row.get("equipment"))),
                ("Ventilation", dash(row.get("ventilation"))),
            ],
            provision_rows=provision_rows,
            lq_eq=(
                (row.get("limited_quantity") or "").strip() or "—",
                "",
            ),
            regulation=edition,
            source=_table().get("source", ""),
        ))
    return pages


def available_un_numbers() -> list[str]:
    """Every UN number the measured ADN table assigns at least one row."""
    return sorted({e["un"] for e in _table()["entries"] if e.get("un")})
