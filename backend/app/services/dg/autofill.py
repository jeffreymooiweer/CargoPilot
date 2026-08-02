"""Automatische invulling van gevaarlijke-stoffengegevens.

Doel: de gebruiker vult zo min mogelijk in. Uit het UN-nummer volgt vrijwel de
volledige classificatie (offline ADR-tabel A + afgeleide modaliteitsgegevens),
uit de reeds ingevoerde colli volgen aantallen en massa's, en daaruit worden de
officiële omschrijvingsregels voor de vervoersdocumenten samengesteld.

Wettelijke basis van de gegenereerde regels:
- ADR/RID/ADN 5.4.1.1.1: UN-nummer, juiste vervoersnaam, gevaarsetiketten,
  verpakkingsgroep, tunnelbeperkingscode, aantal en omschrijving van de colli en
  de totale hoeveelheid per stof.
- ADR 5.4.1.1.1.1: bij gebruik van de 1.1.3.6-vrijstelling moet de totale
  hoeveelheid per vervoerscategorie in het vervoersdocument staan.
- IMDG 5.4.1.4/5.4.1.5: aanvullend vlampunt, marine pollutant en EmS.
- IATA DGR 8.1.6: UN-nummer, PSN, klasse/divisie, verpakkingsgroep, aantal en
  soort colli, netto hoeveelheid per collo en verpakkingsinstructie.

Alle uitkomsten zijn invulhulp; de afzender blijft verantwoordelijk (DISCLAIMER.md).
"""
from __future__ import annotations

import re
from typing import Any

from app.services.dg.database import get_un_entries
from app.services.dg.enrichment import (
    CLASS_DOCUMENT_NOTES,
    PROFILE_DOCUMENT_NOTES,
    clean_value,
    enrich_un_entry,
    parse_hazards,
)

# Velden die nooit automatisch worden overschreven zodra de gebruiker ze vulde.
_AUTOFILL_FIELDS = (
    "proper_shipping_name",
    "class",
    "subsidiary_risks",
    "packing_group",
    "packing_instruction",
    "transport_category",
    "tunnel_code",
    "labels",
    "hazard_number",
    "ems_code",
    "marine_pollutant",
    "cargo_aircraft_only",
    "limited_quantity",
    "excepted_quantity",
    "quantity_packages",
    "gross_mass_per_package",
    "type_of_package",
)


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:[.,]\d+)?", str(value))
    return float(match.group(0).replace(",", ".")) if match else None


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def _un_prefixed(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.upper().startswith(("UN", "ID")) else f"UN {text}"


def derive_product(product: dict[str, Any], language: str = "nl") -> dict[str, Any]:
    """Vul alles in wat uit het UN-nummer volgt; bestaande invoer blijft staan."""
    un = str(product.get("un_number") or "").strip()
    if not un:
        return {}
    entries = get_un_entries(un)
    if not entries:
        return {}
    entry = entries[0]
    extras = enrich_un_entry(entry, language)
    hazards = parse_hazards(entry)

    derived: dict[str, Any] = {
        "proper_shipping_name": (entry.get("name_en") or entry.get("name_de") or "").upper(),
        "class": hazards["division"],
        "subsidiary_risks": "+".join(hazards["subsidiary_risks"]),
        "classification_code": hazards["classification_code"],
        "packing_group": clean_value(entry.get("packing_group")),
        "packing_instruction": clean_value(entry.get("packing_instructions")).split(" ")[0],
        "transport_category": clean_value(entry.get("transport_category")),
        "tunnel_code": clean_value(entry.get("tunnel_code")),
        "labels": clean_value(entry.get("labels")),
        "hazard_number": clean_value(entry.get("hazard_number")),
        "limited_quantity": clean_value(entry.get("limited_quantity")),
        "excepted_quantity": clean_value(entry.get("excepted_quantity")),
    }
    if extras.get("ems_code"):
        derived["ems_code"] = extras["ems_code"]
    if extras.get("environmentally_hazardous"):
        derived["marine_pollutant"] = "P"
    if extras.get("cargo_aircraft_only"):
        derived["cargo_aircraft_only"] = "Y"
    if extras.get("iata_packing_instruction"):
        derived["iata_packing_instruction"] = extras["iata_packing_instruction"]

    # Alleen lege velden aanvullen: handmatige correcties blijven behouden.
    patch = {
        key: value
        for key, value in derived.items()
        if value not in (None, "") and not str(product.get(key) or "").strip()
    }
    hints = {
        key: value
        for key, value in extras.items()
        if key.endswith(("_text", "_note", "_default", "_source", "_description", "_variants",
                         "_options", "_codes"))
    }
    if extras.get("air_forbidden"):
        hints["air_forbidden"] = True
    if extras.get("transport_forbidden"):
        hints["transport_forbidden"] = True
    return {"patch": patch, "hints": hints}


def derive_from_line(product: dict[str, Any], line: dict[str, Any] | None) -> dict[str, Any]:
    """Aantallen en massa's overnemen uit de al ingevoerde colli-regel."""
    if not line:
        return {}
    patch: dict[str, Any] = {}
    quantity = line.get("quantity")
    if quantity not in (None, "") and not str(product.get("quantity_packages") or "").strip():
        patch["quantity_packages"] = str(quantity)
    unit = str(line.get("unit") or "").strip()
    if unit and not str(product.get("type_of_package") or "").strip():
        patch["type_of_package"] = unit
    per_package = _num(line.get("weight_each_kg"))
    if per_package and not str(product.get("gross_mass_per_package") or "").strip():
        patch["gross_mass_per_package"] = f"{_fmt(per_package)} kg"
    return patch


def total_quantity(product: dict[str, Any]) -> tuple[float | None, str]:
    """Totale hoeveelheid van een product: netto per collo × aantal colli."""
    per_package = _num(product.get("net_mass_liters_per_package"))
    count = _num(product.get("quantity_packages"))
    raw = str(product.get("net_mass_liters_per_package") or "")
    unit = "L" if re.search(r"\b(l|ltr|liter|litre)\b", raw, re.IGNORECASE) else "kg"
    if per_package is None:
        total = _num(product.get("adr_total_quantity"))
        return total, unit
    if count is None:
        return per_package, unit
    return per_package * count, unit


def description_line(product: dict[str, Any], profile: str) -> str:
    """Officiële omschrijvingsregel voor het vervoersdocument."""
    psn = str(product.get("proper_shipping_name") or "").strip().upper()
    technical = str(product.get("technical_name") or "").strip()
    if technical:
        psn = f"{psn} ({technical})"
    hazard = str(product.get("class") or "").strip()
    subsidiary = str(product.get("subsidiary_risks") or "").strip()
    if subsidiary:
        hazard = f"{hazard} ({subsidiary})"
    parts = [
        _un_prefixed(product.get("un_number")),
        psn,
        hazard,
        str(product.get("packing_group") or "").strip(),
    ]
    if profile in {"ADR", "RID", "ADN"}:
        tunnel = str(product.get("tunnel_code") or "").strip().strip("()")
        if tunnel:
            parts.append(f"({tunnel})")
    if profile == "IATA_DGR":
        # Uitsluitend een IATA-verpakkingsinstructie tonen: de ADR-instructie
        # (P001, IBC02, …) is voor luchtvracht niet geldig.
        instruction = str(product.get("iata_packing_instruction") or "").strip()
        if instruction:
            parts.append(f"PI {instruction}")
        if str(product.get("cargo_aircraft_only") or "").strip().upper() in {"Y", "YES", "JA", "TRUE", "1"}:
            parts.append("CARGO AIRCRAFT ONLY")
    if profile == "IMDG":
        flashpoint = str(product.get("flashpoint") or "").strip()
        if flashpoint:
            parts.append(f"vlampunt {flashpoint}" if not flashpoint.lower().startswith("v") else flashpoint)
        if str(product.get("marine_pollutant") or "").strip().upper() in {"P", "Y", "YES", "JA", "TRUE", "1"}:
            parts.append("MARINE POLLUTANT")
        ems = str(product.get("ems_code") or "").strip()
        if ems:
            parts.append(f"EmS {ems}")

    line = ", ".join(p for p in parts if p)

    # Aantal en soort colli + totale hoeveelheid (ADR 5.4.1.1.1 f/g).
    count = str(product.get("quantity_packages") or "").strip()
    package = str(product.get("type_of_package") or "").strip()
    packages = " ".join(p for p in [count, package] if p)
    total, unit = total_quantity(product)
    tail = []
    if packages:
        tail.append(packages)
    if total is not None:
        tail.append(f"{_fmt(total)} {unit}")
    if tail:
        line = f"{line}, {', '.join(tail)}"
    return line


def adr_category_totals(entries: list[dict[str, Any]], language: str = "nl") -> dict[str, Any]:
    """Totale hoeveelheid per vervoerscategorie (ADR 5.4.1.1.1.1)."""
    totals: dict[str, dict[str, float]] = {}
    for entry in entries:
        for product in entry.get("products") or []:
            category = str(product.get("transport_category") or "").strip()
            if not category:
                continue
            total, unit = total_quantity(product)
            if total is None:
                continue
            totals.setdefault(category, {}).setdefault(unit, 0.0)
            totals[category][unit] += total

    if not totals:
        return {"statement": "", "categories": []}

    rows = []
    for category in sorted(totals):
        amounts = ", ".join(f"{_fmt(value)} {unit}" for unit, value in sorted(totals[category].items()))
        rows.append({"transport_category": category, "total": amounts})
    prefix = "Totale hoeveelheid per vervoerscategorie" if language == "nl" else "Total quantity per transport category"
    statement = f"{prefix}: " + "; ".join(f"{r['transport_category']}: {r['total']}" for r in rows)
    return {"statement": statement, "categories": rows}


def prepare_entries(
    entries: list[dict[str, Any]],
    lines: list[dict[str, Any]] | None = None,
    profiles: list[str] | None = None,
    language: str = "nl",
) -> dict[str, Any]:
    """Vul DG-posities automatisch aan en stel de documentregels samen."""
    lines_by_id = {line.get("line_id"): line for line in (lines or [])}
    profiles = [p.upper() for p in (profiles or [])] or ["ADR"]
    prepared: list[dict[str, Any]] = []
    hints: list[dict[str, Any]] = []

    for entry in entries:
        products = []
        for index, product in enumerate(entry.get("products") or []):
            merged = dict(product)
            derived = derive_product(merged, language)
            if derived:
                merged.update(derived["patch"])
                if derived["hints"]:
                    hints.append({
                        "line_id": entry.get("line_id"),
                        "product_index": index,
                        "un_number": merged.get("un_number"),
                        **derived["hints"],
                    })
            merged.update(derive_from_line(merged, lines_by_id.get(entry.get("line_id"))))
            # Totale hoeveelheid voor de 1.1.3.6-puntenberekening en de
            # Q-waarde afleiden, zodat de gebruiker die niet hoeft te typen.
            total, unit = total_quantity(merged)
            if total is not None and not str(merged.get("adr_total_quantity") or "").strip():
                merged["adr_total_quantity"] = f"{_fmt(total)} {unit}"
            per_package = merged.get("net_mass_liters_per_package")
            if per_package and not str(merged.get("q_net_quantity") or "").strip():
                merged["q_net_quantity"] = str(per_package)
            products.append(merged)
        prepared.append({**entry, "products": products})

    document_lines: dict[str, list[str]] = {}
    for profile in profiles:
        rows = [
            description_line(product, profile)
            for entry in prepared
            for product in entry["products"]
            if str(product.get("un_number") or "").strip()
        ]
        document_lines[profile] = [row for row in rows if row]

    # Aanvullende documentvereisten die de gebruiker zelf moet aanleveren.
    requirements: list[str] = []
    seen_classes: set[str] = set()
    for entry in prepared:
        for product in entry["products"]:
            base_class = str(product.get("class") or "").split(".")[0]
            division = str(product.get("class") or "")
            for key in (division, base_class):
                note = CLASS_DOCUMENT_NOTES.get(key)
                if note and key not in seen_classes:
                    seen_classes.add(key)
                    requirements.append(note[language if language in note else "nl"])
                    break
    for profile in profiles:
        note = PROFILE_DOCUMENT_NOTES.get(profile)
        if note:
            requirements.append(note[language if language in note else "nl"])

    result: dict[str, Any] = {
        "entries": prepared,
        "document_lines": document_lines,
        "hints": hints,
        "requirements": requirements,
    }
    if {"ADR", "RID", "ADN"} & set(profiles):
        result["adr_category_totals"] = adr_category_totals(prepared, language)
    return result
