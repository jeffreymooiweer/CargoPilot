"""Automatic completion of dangerous goods data.

The aim: the user fills in as little as possible. The UN number yields almost
the complete classification (offline ADR table A plus derived per-mode data),
the package lines already entered yield counts and masses, and from those the
official description lines for the transport documents are composed.

Legal basis of the generated lines:
- ADR/RID/ADN 5.4.1.1.1: UN number, proper shipping name, hazard labels,
  packing group, tunnel restriction code, number and description of the packages
  and the total quantity per substance.
- ADR 5.4.1.1.1.1: when using the 1.1.3.6 exemption, the total quantity per
  transport category must appear in the transport document.
- IMDG 5.4.1.4/5.4.1.5: additionally flashpoint, marine pollutant and EmS.
- IATA DGR 8.1.6: UN number, PSN, class/division, packing group, number and type
  of packages, net quantity per package and packing instruction.

All results are an aid to filling in; the consignor stays responsible
(DISCLAIMER.md).
"""
from __future__ import annotations

import re
from typing import Any

from app.core.languages import pick
from app.services.dg.naming import proper_shipping_name, resolve_for_profile
from app.services.dg.database import get_un_entries
from app.services.dg.enrichment import (
    CLASS_DOCUMENT_NOTES,
    PROFILE_DOCUMENT_NOTES,
    clean_value,
    enrich_un_entry,
    parse_hazards,
)

# Fields that are never overwritten automatically once the user has filled them.
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


def derive_product(
    product: dict[str, Any], language: str = "nl", profiles: list[str] | None = None
) -> dict[str, Any]:
    """Fill in everything that follows from the UN number; existing input stays."""
    un = str(product.get("un_number") or "").strip()
    if not un:
        return {}
    entries = get_un_entries(un)
    if not entries:
        return {}

    # One UN number can have several Table A rows (per packing group), each with
    # its own transport category, LQ and E code. If the user has already filled
    # in the packing group, *that* row should be the source — not silently the
    # first one.
    user_pg = str(product.get("packing_group") or "").strip().upper()
    entry = entries[0]
    if user_pg:
        entry = next(
            (e for e in entries
             if clean_value(e.get("packing_group")).strip().upper() == user_pg),
            entries[0],
        )
    distinct_pgs: list[str] = []
    for candidate in entries:
        pg = clean_value(candidate.get("packing_group")).strip().upper()
        if pg and pg not in distinct_pgs:
            distinct_pgs.append(pg)

    extras = enrich_un_entry(entry, language)
    hazards = parse_hazards(entry)

    derived: dict[str, Any] = {
        "proper_shipping_name": proper_shipping_name(entry, language, profiles),
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

    # Complete empty fields only: manual corrections are preserved.
    patch = {
        key: value
        for key, value in derived.items()
        if value not in (None, "") and not str(product.get(key) or "").strip()
    }
    hints = {
        key: value
        for key, value in extras.items()
        if key.endswith(("_text", "_note", "_default", "_source", "_description", "_variants",
                         "_options", "_codes", "_changes", "_requirement", "_category"))
    }

    # Several packing groups without a choice by the user: the first row has
    # been filled in, but category (a points factor!), LQ and E code differ per
    # row. That must not be a silent choice.
    if len(distinct_pgs) > 1 and not user_pg:
        chosen = clean_value(entry.get("packing_group")).strip().upper()
        variants = "; ".join(
            "PG {pg}: cat {cat}, LQ {lq}, {eq}".format(
                pg=clean_value(e.get("packing_group")).strip().upper() or "—",
                cat=clean_value(e.get("transport_category")) or "—",
                lq=clean_value(e.get("limited_quantity")) or "—",
                eq=clean_value(e.get("excepted_quantity")) or "—",
            )
            for e in entries
            if clean_value(e.get("packing_group")).strip().upper()
        )
        hints["packing_group_note"] = pick(
            {
                "nl": "Deze stof kent meerdere verpakkingsgroepen ({pgs}); verpakkingsgroep "
                      "{chosen} is voorlopig ingevuld. Vervoerscategorie, LQ en E-code "
                      "verschillen per groep ({variants}) — controleer de verpakkingsgroep "
                      "van uw product.",
                "en": "This substance has several packing groups ({pgs}); packing group "
                      "{chosen} was filled in provisionally. Transport category, LQ and E "
                      "code differ per group ({variants}) — verify the packing group of "
                      "your product.",
                "de": "Dieser Stoff hat mehrere Verpackungsgruppen ({pgs}); Verpackungs"
                      "gruppe {chosen} wurde vorläufig eingetragen. Beförderungskategorie, "
                      "LQ und E-Code unterscheiden sich je Gruppe ({variants}) — prüfen "
                      "Sie die Verpackungsgruppe Ihres Produkts.", "fr": "Cette matière comporte plusieurs groupes d'emballage ({pgs}) ; le groupe d'emballage {chosen} a été rempli à titre provisoire. La catégorie de transport, la QL et le code E diffèrent d'un groupe à l'autre ({variants}) — vérifiez le groupe d'emballage de votre produit."},
            language,
        ).format(pgs=", ".join(distinct_pgs), chosen=chosen, variants=variants)

    if extras.get("air_forbidden"):
        hints["air_forbidden"] = True
    if extras.get("transport_forbidden"):
        hints["transport_forbidden"] = True

    # B8: points of attention belong to the active mode. Sea information (EmS,
    # stowage, segregation, marine pollutant) is noise on a pure road leg, and
    # the aviation prohibition says nothing on an inland waterway document.
    # Without profiles nothing is filtered.
    active = {p.upper() for p in (profiles or [])}
    if active:
        def _relevant(key: str) -> bool:
            if key.startswith(("ems_", "imdg_", "marine_pollutant_", "segregation_groups_")):
                return "IMDG" in active
            if key.startswith("air_"):
                return "IATA_DGR" in active
            if key in ("limited_quantity_text", "excepted_quantity_text"):
                return bool({"ADR", "RID", "ADN", "IMDG"} & active)
            return True

        hints = {key: value for key, value in hints.items() if _relevant(key)}

    return {"patch": patch, "hints": hints}


def derive_from_line(product: dict[str, Any], line: dict[str, Any] | None) -> dict[str, Any]:
    """Take counts and masses over from the package line already entered."""
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
    """Total quantity of a product: net per package × number of packages."""
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


def _is_class1(product: dict[str, Any]) -> bool:
    return str(product.get("class") or "").strip().startswith("1")


def adr_quantity(product: dict[str, Any]) -> tuple[float | None, str]:
    """The quantity 1.1.3.6 computes with.

    For class 1 that is the net explosive mass (1.1.3.6.3), not the product
    mass: 50 kg of fireworks is not 50 kg of explosive substance. Without a NEM
    filled in this deliberately yields nothing, so that the points count reports
    "incomplete" instead of computing with the wrong mass.
    """
    if _is_class1(product):
        nem = _num(product.get("net_explosive_mass"))
        return (nem, "kg") if nem is not None else (None, "kg")
    return total_quantity(product)


def description_line(product: dict[str, Any], profile: str) -> str:
    """Official description line for the transport document."""
    # The name follows the document: on an IMDG or IATA line it should be
    # English, even when the consignment was drawn up in German (IMDG 5.4.1.4.1,
    # IATA DGR 8.1.2.1).
    psn = resolve_for_profile(product, profile)[0].upper()
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
    # ADR only. The tunnel restriction code comes from column 15 of ADR Table A
    # and belongs on the road document under 5.4.1.1.1 (k). RID Table A does not
    # have that column and the ADN transport document does not carry it either —
    # "(D/E)" on a CIM or an ADN document is an invented entry on an official
    # piece of paper.
    if profile == "ADR":
        tunnel = str(product.get("tunnel_code") or "").strip().strip("()")
        if tunnel:
            parts.append(f"({tunnel})")
    if profile == "IATA_DGR":
        # Show an IATA packing instruction only: the ADR instruction (P001,
        # IBC02, …) is not valid for air freight.
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

    # Number and type of packages + total quantity (ADR 5.4.1.1.1 f/g).
    count = str(product.get("quantity_packages") or "").strip()
    package = str(product.get("type_of_package") or "").strip()
    packages = " ".join(p for p in [count, package] if p)
    total, unit = total_quantity(product)
    tail = []
    if packages:
        tail.append(packages)
    if total is not None:
        tail.append(f"{_fmt(total)} {unit}")
    # Class 1 on a land document: the total net explosive mass belongs in the
    # transport document (ADR 5.4.1.2.1 (a)).
    if profile in ("ADR", "RID", "ADN") and _is_class1(product):
        nem = _num(product.get("net_explosive_mass"))
        if nem is not None:
            tail.append(f"NEM {_fmt(nem)} kg")
    if tail:
        line = f"{line}, {', '.join(tail)}"
    return line


def adr_category_totals(entries: list[dict[str, Any]], language: str = "nl") -> dict[str, Any]:
    """Totale hoeveelheid per vervoerscategorie (ADR 5.4.1.1.1.1)."""
    totals: dict[str, dict[str, float]] = {}
    for entry in entries:
        for product in entry.get("products") or []:
            if product.get("transport_forbidden"):
                continue
            category = str(product.get("transport_category") or "").strip()
            if not category:
                continue
            total, unit = adr_quantity(product)
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
    prefix = pick(
        {
            "nl": "Totale hoeveelheid per vervoerscategorie",
            "en": "Total quantity per transport category",
            "de": "Gesamtmenge je Beförderungskategorie", "fr": 'Quantité totale par catégorie de transport'},
        language,
    )
    statement = f"{prefix}: " + "; ".join(f"{r['transport_category']}: {r['total']}" for r in rows)
    return {"statement": statement, "categories": rows}


def prepare_entries(
    entries: list[dict[str, Any]],
    lines: list[dict[str, Any]] | None = None,
    profiles: list[str] | None = None,
    language: str = "nl",
) -> dict[str, Any]:
    """Complete DG positions automatically and compose the document lines."""
    lines_by_id = {line.get("line_id"): line for line in (lines or [])}
    profiles = [p.upper() for p in (profiles or [])] or ["ADR"]
    prepared: list[dict[str, Any]] = []
    hints: list[dict[str, Any]] = []

    for entry in entries:
        products = []
        for index, product in enumerate(entry.get("products") or []):
            merged = dict(product)
            derived = derive_product(merged, language, profiles)
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
            # A transport prohibition belongs on the product itself: the points
            # count, document lines and totals then skip such a line instead of
            # computing with it.
            if derived and derived["hints"].get("transport_forbidden"):
                merged["transport_forbidden"] = True
            # Total quantity for the 1.1.3.6 points calculation and the Q value.
            # These two are COMPUTED values and are derived afresh from the
            # current package input on every call. They used to be filled in only
            # when empty, so after a change of count or contents the old totals
            # stayed and the points count and Q value computed with stale
            # figures. Anyone wanting to fix the total sets
            # adr_total_quantity_override or q_net_quantity_override
            # respectively. For class 1, 1.1.3.6.3 computes with the net
            # explosive mass; without a NEM the total deliberately stays empty so
            # the count reports "incomplete".
            total, unit = adr_quantity(merged)
            override = str(merged.get("adr_total_quantity_override") or "").strip()
            if override:
                merged["adr_total_quantity"] = override
            elif total is not None:
                merged["adr_total_quantity"] = f"{_fmt(total)} {unit}"
            elif _is_class1(merged):
                merged.pop("adr_total_quantity", None)
            per_package = merged.get("net_mass_liters_per_package")
            q_override = str(merged.get("q_net_quantity_override") or "").strip()
            if q_override:
                merged["q_net_quantity"] = q_override
            elif per_package:
                merged["q_net_quantity"] = str(per_package)
            products.append(merged)
        prepared.append({**entry, "products": products})

    document_lines: dict[str, list[str]] = {}
    for profile in profiles:
        rows = [
            description_line(product, profile)
            for entry in prepared
            for product in entry["products"]
            # For a substance that may not be offered for carriage there is no
            # document line to compose; the prohibition is already there.
            if str(product.get("un_number") or "").strip()
            and not product.get("transport_forbidden")
        ]
        document_lines[profile] = [row for row in rows if row]

    # Additional document requirements the user has to supply themselves.
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
