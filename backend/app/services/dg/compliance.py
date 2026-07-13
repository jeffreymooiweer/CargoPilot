"""Nalevingscontroles voor gevaarlijke stoffen: ADR 1.1.3.6-punten, ADR 7.5.2
samenlading en IATA Table 9.3.A-segregatie plus Q-waarde (5.0.2.11).

De uitkomsten zijn begeleiding en waarschuwingen — geen juridische vaststelling.
De bevoegde persoon blijft verantwoordelijk (zie DISCLAIMER.md).
"""

import json
import math
import re
from functools import lru_cache
from typing import Any

from app.core.config import get_settings


@lru_cache
def get_compliance_rules() -> dict[str, Any]:
    path = get_settings().config_dir / "dg_compliance.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _lang(language: str) -> str:
    return "en" if str(language).lower().startswith("en") else "nl"


def _num(value: Any) -> float | None:
    """Parse het eerste getal uit een waarde ('333', '5 kg', '12,5 L')."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def _primary_class(product: dict[str, Any]) -> str:
    return str(product.get("class") or "").strip().upper()


def _hazard_tokens(product: dict[str, Any]) -> list[str]:
    """Alle gevaarklassen van een product: hoofdgevaar + nevengevaren."""
    tokens: list[str] = []
    for raw in [product.get("class"), product.get("subsidiary_risks")]:
        for token in re.split(r"[,;/\s()+]+", str(raw or "")):
            token = token.strip().upper()
            if token:
                tokens.append(token)
    return tokens


def _is_class1(token: str) -> bool:
    return bool(re.match(r"^1(\.\d)?[A-S]?$", token)) and not token.startswith(("1.4S",))


def _class1_compat_group(token: str) -> str | None:
    match = re.match(r"^1\.\d([A-S])$", token)
    return match.group(1) if match else None


def _matches_iata_key(token: str, key: str) -> bool:
    """Match een gevarentoken tegen een 9.3.A-sleutel ('1', '2.1', '4.3', …)."""
    if key == "1":
        return _is_class1(token)
    return token == key or token.startswith(f"{key}")


def _product_label(entry: dict[str, Any], product: dict[str, Any], index: int) -> str:
    un = str(product.get("un_number") or "").strip()
    name = str(product.get("proper_shipping_name") or "").strip()
    base = " ".join(x for x in [f"UN {un}" if un else "", name] if x)
    return base or f"{entry.get('vehicle') or entry.get('line_id') or '?'} #{index + 1}"


def _iter_products(entries: list[dict[str, Any]]):
    for entry in entries:
        for index, product in enumerate(entry.get("products") or []):
            yield entry, index, product


def check_adr_points(entries: list[dict[str, Any]], language: str = "nl") -> dict[str, Any]:
    """ADR 1.1.3.6: punten per product, totaal en vrijstellingsstatus."""
    rules = get_compliance_rules()["adr_points"]
    lang = _lang(language)
    categories = rules["categories"]
    threshold = rules["threshold"]

    rows: list[dict[str, Any]] = []
    total = 0.0
    incomplete: list[str] = []
    category0: list[str] = []

    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        category = str(product.get("transport_category") or "").strip()
        quantity = _num(product.get("adr_total_quantity"))
        if category not in categories or quantity is None:
            incomplete.append(label)
            rows.append({
                "product": label,
                "transport_category": category or None,
                "quantity": quantity,
                "points": None,
            })
            continue
        spec = categories[category]
        if category == "0":
            category0.append(label)
            points = None
        else:
            points = round(quantity * (spec["factor"] or 0), 2)
            total += points
        rows.append({
            "product": label,
            "transport_category": category,
            "quantity": quantity,
            "factor": spec["factor"],
            "points": points,
        })

    if category0:
        status = "not_exempt"
    elif incomplete:
        status = "incomplete"
    elif total <= threshold:
        status = "exempt_possible"
    else:
        status = "above_threshold"

    return {
        "rows": rows,
        "total_points": round(total, 2),
        "threshold": threshold,
        "status": status,
        "category0_products": category0,
        "incomplete_products": incomplete,
        "quantity_units_note": rules["quantity_units"][lang],
        "exempt_provisions": rules["exempt_provisions"][lang],
        "still_required": rules["still_required"][lang],
    }


def check_adr_mixed_loading(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, str]]:
    """ADR 7.5.2 / 7.5.4 (CV28): samenladingswaarschuwingen op klasseniveau."""
    rules = get_compliance_rules()["adr_mixed_loading"]
    lang = _lang(language)
    warnings: list[dict[str, str]] = []

    class1_products: list[str] = []
    other_class_products: list[str] = []
    compat_groups: set[str] = set()
    food_separation: list[str] = []

    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        tokens = _hazard_tokens(product)
        primary = _primary_class(product)
        un = str(product.get("un_number") or "").strip()

        if primary.startswith("1") and not primary.endswith("S"):
            class1_products.append(label)
            group = _class1_compat_group(primary)
            if group:
                compat_groups.add(group)
        elif primary and not primary.endswith("S"):
            other_class_products.append(label)

        if any(t.startswith("6.1") or t.startswith("6.2") for t in tokens):
            food_separation.append(label)
        elif primary.startswith("9") and un in rules["cv28_class9_un_numbers"]:
            food_separation.append(label)

    if class1_products and other_class_products:
        warnings.append({
            "rule": "ADR 7.5.2.1",
            "severity": "error",
            "message": rules["rules"]["class1_with_others"][lang],
            "products": ", ".join(class1_products + other_class_products),
        })
    if len(compat_groups) > 1:
        warnings.append({
            "rule": "ADR 7.5.2.2",
            "severity": "warning",
            "message": rules["rules"]["class1_compat_groups"][lang].replace(
                "{groups}", ", ".join(sorted(compat_groups))
            ),
            "products": ", ".join(class1_products),
        })
    if food_separation:
        warnings.append({
            "rule": "ADR CV28 / 7.5.4",
            "severity": "warning",
            "message": rules["rules"]["cv28_foodstuffs"][lang],
            "products": ", ".join(food_separation),
        })
    return warnings


def check_iata_segregation(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, str]]:
    """IATA Table 9.3.A: segregatie tussen colli, inclusief lithium-regel."""
    rules = get_compliance_rules()["iata_segregation"]
    lang = _lang(language)
    warnings: list[dict[str, str]] = []

    products: list[tuple[str, list[str], str]] = []
    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        tokens = _hazard_tokens(product)
        un = str(product.get("un_number") or "").strip()
        products.append((label, tokens, un))

    seen: set[tuple[str, str]] = set()
    for i, (label_a, tokens_a, un_a) in enumerate(products):
        for label_b, tokens_b, un_b in products[i + 1:]:
            for key_a, key_b in rules["incompatible_pairs"]:
                hit = (
                    any(_matches_iata_key(t, key_a) for t in tokens_a)
                    and any(_matches_iata_key(t, key_b) for t in tokens_b)
                ) or (
                    any(_matches_iata_key(t, key_b) for t in tokens_a)
                    and any(_matches_iata_key(t, key_a) for t in tokens_b)
                )
                if hit:
                    pair_id = tuple(sorted((label_a, label_b)))
                    if pair_id in seen:
                        continue
                    seen.add(pair_id)
                    warnings.append({
                        "rule": f"IATA Table 9.3.A ({key_a} × {key_b})",
                        "severity": "error",
                        "message": rules["note"][lang],
                        "products": f"{label_a}  ×  {label_b}",
                    })

            lithium_a = un_a in rules["lithium_battery_un_numbers"]
            lithium_b = un_b in rules["lithium_battery_un_numbers"]
            if lithium_a or lithium_b:
                other_tokens = tokens_b if lithium_a else tokens_a
                if any(
                    _matches_iata_key(t, key)
                    for t in other_tokens
                    for key in rules["lithium_incompatible_with"]
                ):
                    pair_id = tuple(sorted((label_a, label_b, "lithium")))
                    if pair_id not in seen:
                        seen.add(pair_id)
                        warnings.append({
                            "rule": "IATA 9.3.2 (lithiumbatterijen)",
                            "severity": "error",
                            "message": rules["lithium_note"][lang],
                            "products": f"{label_a}  ×  {label_b}",
                        })
    return warnings


def check_q_value(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """IATA 5.0.2.11: Q-waarde per positie voor 'all packed in one'."""
    rules = get_compliance_rules()["q_value"]
    lang = _lang(language)
    results: list[dict[str, Any]] = []

    for entry in entries:
        components: list[dict[str, Any]] = []
        for index, product in enumerate(entry.get("products") or []):
            n = _num(product.get("q_net_quantity"))
            m = _num(product.get("q_max_net_quantity"))
            if n is not None and m:
                components.append({
                    "product": _product_label(entry, product, index),
                    "net_quantity": n,
                    "max_per_package": m,
                    "ratio": round(n / m, 4),
                })
        if len(components) < 2:
            continue
        q_raw = sum(c["ratio"] for c in components)
        q_rounded = math.ceil(q_raw * 10) / 10  # naar boven afronden op 1 decimaal
        results.append({
            "position": entry.get("vehicle") or entry.get("line_id"),
            "components": components,
            "q_value": q_rounded,
            "exceeded": q_rounded > rules["limit"],
            "note": rules["note"][lang],
        })
    return results


def check_compliance(
    entries: list[dict[str, Any]],
    profiles: list[str],
    language: str = "nl",
) -> dict[str, Any]:
    """Voer alle relevante controles uit voor de gekozen regelgevingsprofielen."""
    rules = get_compliance_rules()
    result: dict[str, Any] = {
        "sources": rules["sources"],
        "profiles": profiles,
    }
    normalized = {p.upper() for p in profiles}

    if {"ADR", "RID", "ADN"} & normalized:
        result["adr_points"] = check_adr_points(entries, language)
        result["adr_mixed_loading"] = check_adr_mixed_loading(entries, language)

    if "IATA_DGR" in normalized:
        result["iata_segregation"] = check_iata_segregation(entries, language)
        result["q_values"] = check_q_value(entries, language)
        cao = [
            _product_label(entry, product, index)
            for entry, index, product in _iter_products(entries)
            if str(product.get("cargo_aircraft_only") or "").strip().upper() in {"Y", "YES", "JA", "TRUE", "1"}
        ]
        result["cargo_aircraft_only_products"] = cao

    return result
