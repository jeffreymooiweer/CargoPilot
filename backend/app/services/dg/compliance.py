"""Nalevingscontroles voor gevaarlijke stoffen: ADR 1.1.3.6-punten, ADR 7.5.2
samenlading, de LQ/EQ-grenzen van hoofdstuk 3.4 en 3.5, en IATA Table
9.3.A-segregatie plus Q-waarde (5.0.2.11).

De uitkomsten zijn begeleiding en waarschuwingen — geen juridische vaststelling.
De bevoegde persoon blijft verantwoordelijk (zie DISCLAIMER.md).
"""

import json
import math
import re
from decimal import ROUND_CEILING, Decimal
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.languages import normalise, pick
from app.services.dg import amendment_42_24, dangerous_goods_list
from app.services.regulatory_manifest import stale_rule_sets, summary
from app.services.dg.enrichment import (
    EXCEPTED_QUANTITY_LIMITS,
    card_data_for,
    imdg_code_text,
    imdg_segregation_codes_for,
    parse_hazards,
    segregation_group_label,
    segregation_groups_for,
    segregation_provisions,
)


@lru_cache
def get_compliance_rules() -> dict[str, Any]:
    path = get_settings().config_dir / "dg_compliance.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _lang(language: str) -> str:
    return normalise(language)


def _num(value: Any) -> float | None:
    """Parse het eerste getal uit een waarde ('333', '5 kg', '12,5 L').

    Het teken telt mee: '-5 L' is -5, niet 5. Een negatieve hoeveelheid moet
    als fout bovenkomen, niet stilzwijgend positief worden gemaakt.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value))
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


#: Het weg-, spoor- en binnenvaartregime kennen alle drie een 1.1.3.6 en een
#: samenladingshoofdstuk, maar het zijn niet dezelfde teksten. CargoPilot draagt
#: de ADR-tabellen; die van RID en ADN staan er niet in. Dat stilzwijgend als
#: "RID-uitkomst" presenteren is de gebruiker een zekerheid geven die er niet is,
#: dus wordt de grondslag benoemd zodra hij afwijkt van het gekozen profiel.
LAND_PROFILES = ("ADR", "RID", "ADN")

BASIS_NOTE = {
    "nl": "Berekend met de tabellen van het ADR. {other} kent een eigen "
          "{section}; die staat niet in CargoPilot. Gebruik deze uitkomst als "
          "indicatie en toets hem aan de tekst die voor jouw traject geldt.",
    "en": "Computed with the ADR tables. {other} has its own {section}, which "
          "CargoPilot does not hold. Treat this as indicative and check it "
          "against the text that applies to your leg.",
    "de": "Mit den Tabellen des ADR berechnet. {other} hat einen eigenen "
          "{section}, den CargoPilot nicht enthält. Nehmen Sie das Ergebnis als "
          "Anhaltspunkt und prüfen Sie es an dem für Ihre Strecke geltenden Text.",
}

# For 1.1.3.6 the hedge above is no longer the truth, and saying less than we
# know is its own kind of wrong. RID 1.1.3.6.3 sets out the same five transport
# categories with the same figures (0, 20, 333, 1000, unlimited) and RID
# 1.1.3.6.4 the same multipliers — 50, 3 and 1 — against the same calculated
# value of 1000. What differs is the unit of account: RID counts per wagon or
# large container, ADR per transport unit. Read from RID 2025 p. 29.
RID_POINTS_NOTE = {
    "nl": "RID 1.1.3.6.3 en 1.1.3.6.4 schrijven dezelfde vervoerscategorieën, "
          "dezelfde factoren (50, 3 en 1) en dezelfde waarde van 1000 voor als "
          "het ADR. Het verschil zit in de eenheid: het RID rekent per wagen of "
          "grote container, het ADR per vervoerseenheid.",
    "en": "RID 1.1.3.6.3 and 1.1.3.6.4 prescribe the same transport categories, "
          "the same factors (50, 3 and 1) and the same calculated value of 1000 "
          "as ADR. The difference is the unit: RID counts per wagon or large "
          "container, ADR per transport unit.",
    "de": "RID 1.1.3.6.3 und 1.1.3.6.4 schreiben dieselben "
          "Beförderungskategorien, dieselben Faktoren (50, 3 und 1) und "
          "denselben berechneten Wert von 1000 vor wie das ADR. Der Unterschied "
          "liegt in der Einheit: das RID rechnet je Wagen oder Großcontainer, "
          "das ADR je Beförderungseinheit.",
}

# ADN does not have a points system at all. Its 1.1.3.6.1 exempts a consignment
# in packages when the gross mass of everything stays under 3000 kg and no class
# exceeds its own figure. An ADR points total is therefore not an approximation
# of the ADN answer — it answers a different question — so the two are reported
# separately rather than one standing in for the other.
ADN_POINTS_NOTE = {
    "nl": "Let op: het ADN kent geen puntentelling. ADN 1.1.3.6.1 stelt vrij op "
          "grond van de totale brutomassa (ten hoogste 3000 kg) en een eigen "
          "grens per klasse. Deze punten gelden voor het wegtraject; de "
          "ADN-uitkomst staat er los van in het paneel.",
    "en": "Note: ADN has no points calculation. ADN 1.1.3.6.1 exempts on total "
          "gross mass (at most 3,000 kg) and its own limit per class. These "
          "points apply to the road leg; the ADN outcome is reported separately "
          "in the panel.",
    "de": "Hinweis: das ADN kennt keine Punkteberechnung. ADN 1.1.3.6.1 stellt "
          "anhand der Gesamtbruttomasse (höchstens 3000 kg) und einer eigenen "
          "Grenze je Klasse frei. Diese Punkte gelten für die Straßenstrecke; "
          "das ADN-Ergebnis wird im Panel gesondert ausgewiesen.",
}


def basis_note(profiles: list[str] | None, section: str, language: str) -> str | None:
    """Melding wanneer een ADR-tabel voor RID of ADN wordt gebruikt.

    Voor 1.1.3.6 is de grondslag inmiddels nagelezen in de officiële teksten en
    hoeft er niet meer te worden gehedged: het RID rekent hetzelfde, het ADN
    rekent iets heel anders. Voor de overige hoofdstukken staat de oude,
    voorzichtige melding nog — die zijn nog niet nagelezen.
    """
    selected = {p.upper() for p in (profiles or [])}
    other = sorted(selected & {"RID", "ADN"})
    if not other:
        return None
    if section == "1.1.3.6":
        parts = []
        if "RID" in other:
            parts.append(pick(RID_POINTS_NOTE, language))
        if "ADN" in other:
            parts.append(pick(ADN_POINTS_NOTE, language))
        return " ".join(parts)
    return pick(BASIS_NOTE, language).format(other=" en ".join(other), section=section)


def check_adr_points(
    entries: list[dict[str, Any]], language: str = "nl", profiles: list[str] | None = None
) -> dict[str, Any]:
    """ADR 1.1.3.6: punten per product, totaal en vrijstellingsstatus."""
    rules = get_compliance_rules()["adr_points"]
    lang = _lang(language)
    categories = rules["categories"]
    threshold = rules["threshold"]

    rows: list[dict[str, Any]] = []
    total = 0.0
    incomplete: list[str] = []
    category0: list[str] = []
    forbidden: list[str] = []

    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        # Een stof met vervoersverbod hoort niet in de puntentelling: er valt
        # niets vrij te stellen en "vul de categorie in" naast het rode verbod
        # is verwarring. De regel wordt apart benoemd.
        if product.get("transport_forbidden"):
            forbidden.append(label)
            continue
        category = str(product.get("transport_category") or "").strip()
        quantity = _num(product.get("adr_total_quantity"))
        if category not in categories or quantity is None or quantity <= 0:
            # Ook 0 of negatief is onbruikbaar: -5 L zou het puntentotaal
            # verlagen en een vrijstelling voorspiegelen die er niet is.
            incomplete.append(label)
            rows.append({
                "product": label,
                "transport_category": category or None,
                "quantity": quantity,
                "points": None,
            })
            continue
        spec = categories[category]
        factor = spec["factor"]
        note_a = False
        # ADR/RID 1.1.3.6.3 note (a): nine UN numbers of transport category 1
        # may be carried up to 50 kg instead of 20 kg, and RID 1.1.3.6.4 spells
        # out the multiplier that goes with it — times 20, not times 50. Read
        # from ADR 2025 Vol. I and RID 2025; see scripts/read_land_regulations.py.
        #
        # Counting them at 50 is not a harmless over-estimate. 50 kg of chlorine
        # scored 2500 and lost an exemption the text grants at exactly 1000, so
        # the application demanded orange plates, a driver certificate and an
        # ADR vehicle for a load that does not need them.
        if category == "1" and _num(rules.get("category_1_note_a", {}).get("factor")):
            exception = rules["category_1_note_a"]
            if str(product.get("un_number") or "").strip().lstrip("UN ").strip() in set(
                exception["un_numbers"]
            ):
                factor = exception["factor"]
                note_a = True
        if category == "0":
            category0.append(label)
            points = None
        else:
            points = round(quantity * (factor or 0), 2)
            total += points
        rows.append({
            "product": label,
            "transport_category": category,
            "quantity": quantity,
            "factor": factor,
            "points": points,
            **({"note_a": True} if note_a else {}),
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
        "forbidden_products": forbidden,
        "quantity_units_note": pick(rules["quantity_units"], lang),
        "exempt_provisions": pick(rules["exempt_provisions"], lang),
        "still_required": pick(rules["still_required"], lang),
        "basis": "ADR 1.1.3.6",
        "basis_note": basis_note(profiles, "1.1.3.6", language),
    }


def _adn_row_matches(rule: dict[str, Any], product: dict[str, Any]) -> bool:
    """Does this ADN table row describe this product?"""
    selector = rule["selector"]
    if selector in {"all", "other"}:
        return True
    packing_group = str(product.get("packing_group") or "").strip().upper()
    if selector == "pg_i":
        return packing_group == "I"
    if selector == "toxic_groups" or selector == "group_f":
        # ADN reads the class 2 group out of the classification code: the letters
        # after the digit in 2.2.2.1.3, e.g. 2TF, 4F, 1O.
        code = str(product.get("classification_code") or "").strip().upper()
        letters = "".join(character for character in code if character.isalpha())
        if not letters:
            return False
        return letters in {group.upper() for group in rule.get("groups", [])}
    if selector == "label_1":
        # "for which a danger label of model No. 1 is required in column (5)".
        labels = {token.strip() for token in _hazard_tokens(product)}
        return "1" in labels
    if selector == "category_a":
        # Class 6.2 category A is carried in the UN number, not in a column.
        return str(product.get("un_number") or "").strip() in {"2814", "2900", "3549"}
    if selector == "excepted_packages":
        return str(product.get("un_number") or "").strip() in set(rule.get("un_numbers", []))
    return False


def _adn_limit_for(product: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The first row of the ADN table that fits, which is the applicable one.

    Order matters and the table is written to be read in order: the specific
    rows of a class come before its "any other substances" row, so a class 3
    packing group I substance is caught by the 300 kg row and never reaches the
    3000 kg one.
    """
    primary = _primary_class(product)
    for rule in rules:
        if rule["class"] != primary:
            continue
        if _adn_row_matches(rule, product):
            return rule
    return None


def check_adn_exemption(
    entries: list[dict[str, Any]], language: str = "nl"
) -> dict[str, Any]:
    """ADN 1.1.3.6.1: vrijstelling voor vervoer in colli aan boord van een schip.

    Het ADN kent geen puntentelling. Het stelt vrij wanneer de brutomassa van
    alle gevaarlijke goederen samen onder de 3000 kg blijft én geen enkele
    klasse boven haar eigen grens uit komt — 0, 300 of 3000 kg, afhankelijk van
    verpakkingsgroep, groep of etiket. Voor vervoer in tanks geldt de
    vrijstelling in het geheel niet.

    Tot v1.32.0 kreeg een ADN-zending de ADR-puntentelling te zien. Dat is geen
    benadering van dit antwoord maar een antwoord op een andere vraag: 1200 kg
    van een vloeistof in verpakkingsgroep III kost 1200 ADR-punten en verliest
    daar de vrijstelling, terwijl het ADN dezelfde zending vrijstelt zolang het
    totaal onder 3000 kg blijft.
    """
    config = get_compliance_rules()["adn_exemption"]
    lang = _lang(language)
    rules = config["rules"]
    cap = float(config["total_gross_mass_kg"])

    rows: list[dict[str, Any]] = []
    total = 0.0
    incomplete: list[str] = []
    over_class: list[dict[str, Any]] = []
    per_limit: dict[tuple[str, str], float] = {}

    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        if product.get("transport_forbidden"):
            continue
        rule = _adn_limit_for(product, rules)
        mass = _num(product.get("adr_total_quantity"))
        if rule is None or mass is None or mass <= 0:
            incomplete.append(label)
            rows.append({"product": label, "limit": rule["limit"] if rule else None,
                         "quantity": mass, "class": _primary_class(product)})
            continue
        total += mass
        key = (rule["class"], rule["selector"])
        per_limit[key] = per_limit.get(key, 0.0) + mass
        rows.append({
            "product": label,
            "class": rule["class"],
            "selector": rule["selector"],
            "limit": rule["limit"],
            "quantity": mass,
        })

    for (class_name, selector), carried in sorted(per_limit.items()):
        limit = next(
            rule["limit"] for rule in rules
            if rule["class"] == class_name and rule["selector"] == selector
        )
        if carried > limit:
            over_class.append({"class": class_name, "selector": selector,
                               "limit": limit, "carried": round(carried, 2)})

    if incomplete:
        status = "incomplete"
    elif over_class:
        status = "not_exempt"
    elif total > cap:
        status = "above_threshold"
    else:
        status = "exempt_possible"

    return {
        "rows": rows,
        "total_gross_mass_kg": round(total, 2),
        "threshold": cap,
        "status": status,
        "over_class_limit": over_class,
        "incomplete_products": incomplete,
        "basis": "ADN 1.1.3.6.1",
        "conditions": pick(config["conditions"], lang),
        "note": pick(
            {
                "nl": "Het ADN stelt vrij op brutomassa, niet met punten: het "
                      "totaal blijft onder 3000 kg en geen klasse komt boven haar "
                      "eigen grens. Vervoer in tanks is nooit vrijgesteld. De "
                      "voorwaarden van 1.1.3.6.2 blijven gelden.",
                "en": "ADN exempts on gross mass, not on points: the total stays "
                      "under 3,000 kg and no class exceeds its own limit. Carriage "
                      "in tanks is never exempt. The conditions of 1.1.3.6.2 "
                      "continue to apply.",
                "de": "Das ADN stellt anhand der Bruttomasse frei, nicht mit "
                      "Punkten: die Summe bleibt unter 3000 kg und keine Klasse "
                      "überschreitet ihre eigene Grenze. Beförderung in Tanks ist "
                      "nie freigestellt. Die Bedingungen nach 1.1.3.6.2 gelten "
                      "weiter.",
            },
            lang,
        ),
    }


def check_adr_mixed_loading(
    entries: list[dict[str, Any]], language: str = "nl", profiles: list[str] | None = None
) -> list[dict[str, str]]:
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
            "message": pick(rules["rules"]["class1_with_others"], lang),
            "products": ", ".join(class1_products + other_class_products),
        })
    if len(compat_groups) > 1:
        warnings.append({
            "rule": "ADR 7.5.2.2",
            "severity": "warning",
            "message": pick(rules["rules"]["class1_compat_groups"], lang).replace(
                "{groups}", ", ".join(sorted(compat_groups))
            ),
            "products": ", ".join(class1_products),
        })
    if food_separation:
        warnings.append({
            "rule": "ADR CV28 / 7.5.4",
            "severity": "warning",
            "message": pick(rules["rules"]["cv28_foodstuffs"], lang),
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
                        "message": pick(rules["note"], lang),
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
                            "message": pick(rules["lithium_note"], lang),
                            "products": f"{label_a}  ×  {label_b}",
                        })
    return warnings


def _imdg_row_key(token: str, class_order: list[str]) -> str | None:
    """Map een gevarentoken op een rij van de IMDG-segregatietabel."""
    token = token.strip().upper()
    if not token:
        return None
    if token.startswith("1"):
        # 1.4S valt buiten de tabel voor de meeste combinaties, maar de code
        # kent 1.4 wel als eigen rij; compatibiliteitsgroep negeren we hier.
        division = re.match(r"^1(\.\d)?", token)
        if not division:
            return None
        value = division.group(0)
        if value in {"1.1", "1.2", "1.5", "1"}:
            return "1.1-1.2-1.5"
        if value in {"1.3", "1.6"}:
            return "1.3-1.6"
        if value == "1.4":
            return "1.4"
        return None
    for key in class_order:
        if key == token:
            return key
    # '2' zonder divisie of '6' zonder divisie kan niet betrouwbaar worden
    # ingedeeld; die slaan we over in plaats van te gokken.
    return None


def check_imdg_segregation(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """IMDG 7.2.4: scheiding tussen colli op basis van de klassescheidingstabel."""
    rules = get_compliance_rules().get("imdg_segregation")
    if not rules:
        return []
    lang = _lang(language)
    class_order: list[str] = rules["class_order"]
    table: dict[str, list[str]] = rules["table"]
    codes: dict[str, dict[str, str]] = rules["codes"]

    products: list[tuple[str, list[str]]] = []
    for entry, index, product in _iter_products(entries):
        keys: list[str] = []
        primary = _imdg_row_key(_primary_class(product), class_order)
        if primary:
            keys.append(primary)
        # IMDG 7.2.3.3: een nevengevaar van klasse 1 wordt voor de segregatie
        # behandeld als divisie 1.3.
        for token in re.split(r"[,;/\s()+]+", str(product.get("subsidiary_risks") or "")):
            token = token.strip().upper()
            if not token:
                continue
            key = "1.3-1.6" if token.startswith("1") else _imdg_row_key(token, class_order)
            if key and key not in keys:
                keys.append(key)
        if keys:
            products.append((_product_label(entry, product, index), keys))

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for i, (label_a, keys_a) in enumerate(products):
        for label_b, keys_b in products[i + 1:]:
            worst = ""
            worst_pair = ("", "")
            for key_a in keys_a:
                for key_b in keys_b:
                    value = table[key_a][class_order.index(key_b)]
                    if value in {"1", "2", "3", "4"} and (not worst or int(value) > int(worst)):
                        worst = value
                        worst_pair = (key_a, key_b)
                    elif value == "*" and not worst:
                        worst = "*"
                        worst_pair = (key_a, key_b)
            if not worst:
                continue
            pair_id = tuple(sorted((label_a, label_b)))
            if pair_id in seen:
                continue
            seen.add(pair_id)
            warnings.append({
                "rule": f"IMDG 7.2.4 ({worst_pair[0]} × {worst_pair[1]})",
                "severity": "error" if worst in {"3", "4"} else "warning",
                "code": worst,
                "message": pick(codes[worst], lang),
                "products": f"{label_a}  ×  {label_b}",
                "source": "table",
                "pair": "|".join(pair_id),
            })
    return warnings


def _compat_group(product: dict[str, Any]) -> str | None:
    """Compatibiliteitsgroep van een klasse 1-product (bijv. 1.4G → 'G')."""
    for raw in (product.get("classification_code"), product.get("class"), product.get("subsidiary_risks")):
        match = re.search(r"\b1\.\d\s*([A-HJ-NPS])\b", str(raw or "").upper())
        if match:
            return match.group(1)
    return None


def check_imdg_class1_compatibility(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.7.1.4: toegestane gemengde stuwage van compatibiliteitsgroepen."""
    rules = get_compliance_rules().get("imdg_class1_compatibility")
    if not rules:
        return []
    lang = _lang(language)
    order: list[str] = rules["group_order"]
    matrix: dict[str, list[str]] = rules["matrix"]
    special: dict[str, dict[str, str]] = rules.get("special_notes", {})

    products: list[tuple[str, str]] = []
    for entry, index, product in _iter_products(entries):
        group = _compat_group(product)
        if group and group in order:
            products.append((_product_label(entry, product, index), group))

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for i, (label_a, group_a) in enumerate(products):
        for label_b, group_b in products[i + 1:]:
            pair_id = tuple(sorted((label_a, label_b)))
            if pair_id in seen:
                continue
            permitted = matrix[group_a][order.index(group_b)] == "X"
            note = special.get(group_a) or special.get(group_b)
            if not permitted:
                seen.add(pair_id)
                warnings.append({
                    "rule": f"IMDG 7.2.7.1.4 ({group_a} × {group_b})",
                    "severity": "error",
                    "message": pick(rules["note"], lang),
                    "products": f"{label_a}  ×  {label_b}",
                })
            elif note and group_a != group_b:
                seen.add(pair_id)
                warnings.append({
                    "rule": f"IMDG 7.2.7.1.4 ({group_a} × {group_b})",
                    "severity": "warning",
                    "message": pick(note, lang),
                    "products": f"{label_a}  ×  {label_b}",
                })
    return warnings


# Scheidingsgroepen die onderling niet samen mogen (IMDG 7.2.5 in samenhang met
# kolom 16b): de klassieke gevaarlijke combinaties.
_SGG_CONFLICTS: list[tuple[str, str, dict[str, str]]] = [
    ("SGG1", "SGG18", {
        "nl": "zuren en alkaliën",
        "en": "acids and alkalis",
        "de": "Säuren und Laugen"}),
    ("SGG1", "SGG6", {
        "nl": "zuren en cyaniden (ontwikkeling van blauwzuur)",
        "en": "acids and cyanides (release of hydrogen cyanide)",
        "de": "Säuren und Cyanide (Freisetzung von Blausäure)"}),
    ("SGG1", "SGG5", {
        "nl": "zuren en chlorieten (ontwikkeling van chloordioxide)",
        "en": "acids and chlorites (release of chlorine dioxide)",
        "de": "Säuren und Chlorite (Freisetzung von Chlordioxid)"}),
    ("SGG1", "SGG8", {
        "nl": "zuren en hypochlorieten (ontwikkeling van chloorgas)",
        "en": "acids and hypochlorites (release of chlorine gas)",
        "de": "Säuren und Hypochlorite (Freisetzung von Chlorgas)"}),
    ("SGG1", "SGG12", {
        "nl": "zuren en nitrieten (ontwikkeling van nitreuze dampen)",
        "en": "acids and nitrites (release of nitrous fumes)",
        "de": "Säuren und Nitrite (Freisetzung nitroser Gase)"}),
    ("SGG1", "SGG17", {
        "nl": "zuren en aziden (vorming van explosief waterstofazide)",
        "en": "acids and azides (formation of explosive hydrazoic acid)",
        "de": "Säuren und Azide (Bildung von explosiver Stickstoffwasserstoffsäure)"}),
    ("SGG1", "SGG14", {
        "nl": "zuren en permanganaten",
        "en": "acids and permanganates",
        "de": "Säuren und Permanganate"}),
    ("SGG1", "SGG15", {
        "nl": "zuren en metaalpoeders (ontwikkeling van waterstof)",
        "en": "acids and powdered metals (release of hydrogen)",
        "de": "Säuren und Metallpulver (Freisetzung von Wasserstoff)"}),
    ("SGG16", "SGG1", {
        "nl": "peroxiden en zuren",
        "en": "peroxides and acids",
        "de": "Peroxide und Säuren"}),
]


def check_imdg_segregation_groups(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.5/3.1.4.4: onverenigbare scheidingsgroepen binnen de zending."""
    lang = _lang(language)
    products: list[tuple[str, set[str]]] = []
    for entry, index, product in _iter_products(entries):
        groups = set(segregation_groups_for(product.get("un_number", ""),
                                            str(product.get("packing_group") or "")))
        # Handmatig ingevulde groepen tellen ook mee.
        for token in re.split(r"[,;/\s]+", str(product.get("segregation_group") or "")):
            if token.strip().upper().startswith("SGG"):
                groups.add(token.strip().upper())
        if groups:
            products.append((_product_label(entry, product, index), groups))

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for i, (label_a, groups_a) in enumerate(products):
        for label_b, groups_b in products[i + 1:]:
            for code_a, code_b, names in _SGG_CONFLICTS:
                hit = (code_a in groups_a and code_b in groups_b) or (
                    code_b in groups_a and code_a in groups_b
                )
                if not hit:
                    continue
                key = (*sorted((label_a, label_b)), f"{code_a}-{code_b}")
                if key in seen:
                    continue
                seen.add(key)
                warnings.append({
                    "rule": f"IMDG 7.2.5 ({code_a} × {code_b})",
                    "severity": "warning",
                    "message": pick(
                        {
                            "nl": "Scheidingsgroepen {groups}: kolom 16b van de Dangerous "
                                  "Goods List schrijft hier scheiding voor. Controleer de "
                                  "vermelding per stof.",
                            "en": "Segregation groups {groups}: column 16b of the Dangerous "
                                  "Goods List prescribes segregation here. Check the entry "
                                  "per substance.",
                            "de": "Trenngruppen {groups}: Spalte 16b der Dangerous Goods List "
                                  "schreibt hier eine Trennung vor. Prüfen Sie den Eintrag je "
                                  "Stoff.",
                        },
                        lang,
                    ).format(groups=pick(names, lang)),
                    "products": f"{label_a}  ×  {label_b}",
                })
    return warnings


# Hoe streng een scheidingsvoorschrift is, in gewone taal.
_ACTION_TEXT = {
    # De Duitse IMDG-uitgave onderscheidt "entfernt von" (away from) en
    # "getrennt von" (separated from); dat verschil is hier het hele punt.
    "away_from": {
        "nl": "uit de buurt van",
        "en": "away from",
        "de": "entfernt von",
    },
    "separated_from": {
        "nl": "gescheiden van",
        "en": "separated from",
        "de": "getrennt von",
    },
    "separated_by_compartment": {
        "nl": "gescheiden door een volledig compartiment of ruim van",
        "en": "separated by a complete compartment or hold from",
        "de": "durch eine vollständige Abteilung oder einen vollständigen Laderaum getrennt von",
    },
    "separated_longitudinally": {
        "nl": "in de lengterichting gescheiden door een tussenliggend compartiment of ruim van",
        "en": "separated longitudinally by an intervening complete compartment or hold from",
        "de": "in Längsrichtung durch eine dazwischenliegende vollständige Abteilung oder "
              "einen vollständigen Laderaum getrennt von",
    },
}

# Dezelfde vier scheidingscodes als in de tabel van 7.2.4, zodat een SG-code en
# een tabelwaarde met elkaar te vergelijken zijn (7.2.3.1).
_ACTION_CODE = {
    "away_from": "1",
    "separated_from": "2",
    "separated_by_compartment": "3",
    "separated_longitudinally": "4",
}


def _classes_of(product: dict[str, Any]) -> set[str]:
    """Hoofdklasse, divisie en nevengevaren van een collo."""
    found: set[str] = set()
    for field in ("class", "subsidiary_risks", "labels"):
        for token in re.split(r"[+,;/\s]+", str(product.get(field) or "")):
            token = token.strip().strip("()")
            if token and re.fullmatch(r"\d(?:\.\d[A-Z]?)?", token):
                found.add(token)
    return found


def _matches_class(target: str, classes: set[str]) -> bool:
    """"class 5.1" raakt 5.1; "class 1" raakt elke divisie van klasse 1."""
    if target in classes:
        return True
    if "." not in target:
        return any(c.split(".")[0] == target for c in classes)
    return False


def _wording(code: str, rules: dict[str, Any]) -> str:
    """De omschrijving van een SG-code, bij voorkeur die van de code zelf.

    Hoofdstuk 7.2.8 geeft de officiële formulering; de zin die van de UN-kaart
    kwam is een parafrase en blijft alleen over als terugval.
    """
    return imdg_code_text(code) or str(rules.get(code, {}).get("text", ""))


def check_imdg_segregation_provisions(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG kolom 16b: de scheidingsvoorschriften (SG) van de stof zelf.

    De scheidingstabel van 7.2.4 werkt op klasse; kolom 16b legt daarbovenop
    voorschriften per stof. Die codes komen nu uit de Dangerous Goods List
    zelf, in de stand van 42-24, en niet langer alleen uit de UN-kaarten van
    41-22 — die dekten lang niet elke stof. Hier wordt gekeken of een andere
    partij in dezelfde zending het doel van zo'n voorschrift is.
    """
    lang = _lang(language)
    rules = segregation_provisions()

    parties: list[dict[str, Any]] = []
    for entry, index, product in _iter_products(entries):
        un = str(product.get("un_number") or "").strip()
        packing_group = str(product.get("packing_group") or "").strip()
        groups = set(segregation_groups_for(un, packing_group))
        for token in re.split(r"[,;/\s]+", str(product.get("segregation_group") or "")):
            if token.strip().upper().startswith("SGG"):
                groups.add(token.strip().upper())
        parties.append({
            "label": _product_label(entry, product, index),
            "un": "".join(ch for ch in un if ch.isdigit()).zfill(4) if un else "",
            "codes": imdg_segregation_codes_for(un, packing_group),
            "classes": _classes_of(product),
            "groups": groups,
        })

    config = get_compliance_rules()
    named = config.get("imdg_segregation_named_targets", {})
    cargo = config.get("imdg_segregation_cargo_requirements", {})

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    # Voorschriften die gewone lading noemen — levensmiddelen, oliën, geur-
    # absorberende lading. De app weet niet wat er verder aan boord gaat, dus
    # deze worden gemeld zodra de stof meegaat, net als de ADR CV28-melding.
    raised_cargo: set[tuple[str, str]] = set()
    for source in parties:
        for code in source["codes"]:
            requirement = cargo.get(code)
            if not isinstance(requirement, dict):
                continue
            # SG26 geldt alleen náást bepaalde klassen; de rest altijd.
            needed = requirement.get("classes")
            if needed and not any(
                any(_matches_class(t, other["classes"]) for t in needed)
                for other in parties if other is not source
            ):
                continue
            key = (source["label"], code)
            if key in raised_cargo:
                continue
            raised_cargo.add(key)
            warnings.append({
                "rule": f"IMDG 16b ({code})",
                "severity": "warning",
                "message": f"{pick(requirement, lang)} {_wording(code, rules)}".strip(),
                "products": source["label"],
            })

    for source in parties:
        for code in source["codes"]:
            rule = rules.get(code)
            if not rule:
                continue

            # Voorschriften die een stof bij naam noemen: welke UN-nummers dat
            # zijn, staat in dg_compliance.json — te controleren en aan te passen.
            target = named.get(code)
            if isinstance(target, dict):
                for other in parties:
                    if other is source:
                        continue
                    by_un = other["un"] in (target.get("un") or [])
                    by_group = any(g in other["groups"] for g in target.get("groups") or [])
                    by_class = any(
                        _matches_class(t, other["classes"]) for t in target.get("classes") or []
                    )
                    if target.get("require_both"):
                        hit = by_class and by_group
                    else:
                        hit = by_un or by_group or by_class
                    if not hit:
                        continue
                    key = (source["label"], other["label"], code)
                    if key in seen:
                        continue
                    seen.add(key)
                    caveat = ""
                    if target.get("broader"):
                        caveat = pick(
                            {
                                "nl": " Gematcht op de scheidingsgroep, die ruimer is dan de "
                                      "tekst; controleer.",
                                "en": " Matched on the segregation group, which is broader "
                                      "than the wording; verify.",
                                "de": " Über die Trenngruppe zugeordnet, die weiter reicht als "
                                      "der Wortlaut; bitte prüfen.",
                            },
                            lang,
                        )
                    warnings.append({
                        "rule": f"IMDG 16b ({code})",
                        "severity": "warning",
                        "message": f"{_wording(code, rules)}{caveat}",
                        "products": f"{source['label']}  \u00d7  {other['label']}",
                    })
                continue

            if rule.get("informational") or not rule.get("targets"):
                continue
            targets = rule["targets"]
            for other in parties:
                if other is source:
                    continue
                # Een uitzondering in het voorschrift ("behalve 1.4S") sluit
                # die partij uit; anders zou de app waarschuwen voor iets dat
                # de Code juist toestaat.
                if any(c in other["classes"] for c in rule.get("excepted_classes") or []):
                    continue
                hit_class = next(
                    (t for t in targets.get("classes", []) if _matches_class(t, other["classes"])),
                    None,
                )
                hit_group = next(
                    (g for g in targets.get("groups", []) if g in other["groups"]), None
                )
                if not hit_class and not hit_group:
                    continue
                key = (source["label"], other["label"], code)
                if key in seen:
                    continue
                seen.add(key)
                action = pick(
                    _ACTION_TEXT.get(str(rule.get("action")), {}),
                    lang,
                    pick(_ACTION_TEXT["separated_from"], lang),
                )
                # "SGG1" zegt niets; "SGG1 (zuren)" wel.
                if hit_class:
                    what = pick(
                        {"nl": "klasse {c}", "en": "class {c}", "de": "Klasse {c}"}, lang
                    ).format(c=hit_class)
                else:
                    what = f"{hit_group} ({segregation_group_label(hit_group, lang)})"
                warnings.append({
                    "rule": f"IMDG 16b ({code})",
                    "severity": "warning",
                    "message": pick(
                        {
                            "nl": "Stuw {action} {what}. {wording}",
                            "en": "Stow {action} {what}. {wording}",
                            "de": "Stauen Sie {action} {what}. {wording}",
                        },
                        lang,
                    ).format(action=action, what=what, wording=_wording(code, rules)),
                    "products": f"{source['label']}  \u00d7  {other['label']}",
                    "source": "column_16b",
                    "code": _ACTION_CODE.get(str(rule.get("action")), ""),
                    "pair": "|".join(sorted((source["label"], other["label"]))),
                })
    return warnings


def apply_column_16b_precedence(
    findings: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.3.1: bij strijdige bepalingen gaat kolom 16b altijd voor.

    De klassescheidingstabel van 7.2.4 en de stof-specifieke SG-codes van kolom
    16b kunnen voor hetzelfde paar iets anders zeggen. De code laat daarover
    geen twijfel bestaan: "In case of conflicting provisions, the provisions of
    column 16b of the Dangerous Goods List, always take precedence."

    Er wordt niets verwijderd. Beide bevindingen blijven staan met de bepaling
    erbij die volgens de code voorgaat, zodat zichtbaar is waarom de ene de
    andere opzij zet. Een terechte melding wegnemen is erger dan er \u00e9\u00e9n te veel
    tonen; dat is dezelfde afweging als bij de vrijstellingen van 7.2.6.3.
    """
    lang = _lang(language)
    by_pair: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for finding in findings:
        pair = finding.get("pair")
        origin = finding.get("source")
        if pair and origin in {"table", "column_16b"}:
            by_pair.setdefault(pair, {}).setdefault(origin, []).append(finding)

    for buckets in by_pair.values():
        table = buckets.get("table") or []
        column = [f for f in buckets.get("column_16b") or [] if f.get("code")]
        if not table or not column:
            continue
        # Meerdere SG-codes kunnen op hetzelfde paar slaan, in beide richtingen.
        # De strengste bepaalt wat er moet gebeuren; alle codes op dat niveau
        # krijgen de vermelding, want ze gaan er allemaal even hard voor.
        strictest_code = max(int(f["code"]) for f in column)
        governing = [f for f in column if int(f["code"]) == strictest_code]
        rules = [f["rule"] for f in governing]
        for finding in table:
            if str(finding.get("code")) == str(strictest_code):
                continue  # Geen strijd: beide bepalingen komen op hetzelfde uit.
            finding["superseded_by"] = rules
            finding["severity"] = "info"
            finding["message"] += pick(
                {
                    "nl": " Let op 7.2.3.1: {rules} in kolom 16b gaat hierop voor "
                          "(scheidingscode {code} in plaats van {was}).",
                    "en": " Note 7.2.3.1: {rules} in column 16b takes precedence over this "
                          "(segregation code {code} instead of {was}).",
                    "de": " Beachten Sie 7.2.3.1: {rules} in Spalte 16b geht dem vor "
                          "(Trennkennzahl {code} statt {was}).",
                },
                lang,
            ).format(rules=", ".join(rules), code=strictest_code, was=finding["code"])
        for finding in governing:
            finding["takes_precedence_over"] = [f["rule"] for f in table]
            finding["message"] += pick(
                {
                    "nl": " Deze bepaling uit kolom 16b gaat volgens 7.2.3.1 voor op de "
                          "klassescheidingstabel.",
                    "en": " Per 7.2.3.1 this column 16b provision takes precedence over the "
                          "class segregation table.",
                    "de": " Diese Bestimmung aus Spalte 16b geht nach 7.2.3.1 der "
                          "Klassentrenntabelle vor.",
                },
                lang,
            )
            if strictest_code >= 3:
                finding["severity"] = "error"
    return findings


def check_imdg_segregation_exemptions(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.6.3: stoffen in dezelfde tabel hoeven niet gescheiden te worden.

    Dit is de vrijstelling waar SG72 in kolom 16b naar verwijst. De app haalt er
    géén waarschuwing mee weg — een terechte melding onderdrukken is erger dan
    een overbodige tonen — maar meldt de vrijstelling ernaast, met tabel en al.
    Zo staan de bevinding en haar rechtsgrond samen in beeld en blijft de keuze
    bij de afzender.
    """
    config = get_compliance_rules().get("imdg_segregation_exemptions")
    if not config:
        return []
    lang = _lang(language)
    tables = config["tables"]

    parties: list[tuple[str, str]] = []
    for entry, index, product in _iter_products(entries):
        un = "".join(ch for ch in str(product.get("un_number") or "") if ch.isdigit())
        if un:
            parties.append((_product_label(entry, product, index), un.zfill(4)))

    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for i, (label_a, un_a) in enumerate(parties):
        for label_b, un_b in parties[i + 1:]:
            for name, members in tables.items():
                if un_a not in members or un_b not in members:
                    continue
                key = (*sorted((label_a, label_b)), name)
                if key in seen:
                    continue
                seen.add(key)
                extra = ""
                if name == "7.2.6.3.4":
                    extra = pick(
                        {
                            "nl": " Let op 7.2.6.4: de gevaarlijke reacties van 7.2.6.1.1 "
                                  "t/m 7.2.6.1.4 blijven gelden.",
                            "en": " Note 7.2.6.4: the dangerous reactions of 7.2.6.1.1 to "
                                  "7.2.6.1.4 continue to apply.",
                            "de": " Beachten Sie 7.2.6.4: die gefährlichen Reaktionen nach "
                                  "7.2.6.1.1 bis 7.2.6.1.4 gelten weiterhin.",
                        },
                        lang,
                    )
                findings.append({
                    "rule": f"IMDG {name}",
                    "severity": "info",
                    "message": pick(
                        {
                            "nl": "Beide stoffen staan in tabel {name}: hiertussen hoeft geen "
                                  "scheiding te worden toegepast.{extra}",
                            "en": "Both substances appear in table {name}: no segregation "
                                  "needs to be applied between them.{extra}",
                            "de": "Beide Stoffe stehen in Tabelle {name}: zwischen ihnen ist "
                                  "keine Trennung anzuwenden.{extra}",
                        },
                        lang,
                    ).format(name=name, extra=extra),
                    "products": f"{label_a}  \u00d7  {label_b}",
                })
    return findings


def append_class8_pair_exception(
    entries: list[dict[str, Any]], findings: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.6.5 naast het betrokken paar, niet alleen als algemene tekst.

    Twee stoffen van klasse 8, verpakkingsgroep II of III, die volgens kolom
    16b gescheiden moeten blijven, mogen onder 7.2.6.5 tóch samen in colli tot
    30 L/30 kg — mits ze niet gevaarlijk met elkaar reageren en het document de
    verklaring van 5.4.1.5.11.3 draagt. Dat is dezelfde afweging als bij
    7.2.6.3: de vrijstelling wordt gemeld, de waarschuwing blijft staan en de
    keuze blijft bij de afzender.
    """
    lang = _lang(language)
    eligible: set[str] = set()
    for entry, index, product in _iter_products(entries):
        primary = _primary_class(product)
        pg = str(product.get("packing_group") or "").strip().upper()
        if primary.startswith("8") and pg in {"II", "III"}:
            eligible.add(_product_label(entry, product, index))

    if len(eligible) < 2:
        return findings

    seen: set[tuple[str, str]] = set()
    extra: list[dict[str, Any]] = []
    for finding in findings:
        if finding.get("severity") not in {"warning", "error"}:
            continue
        parts = [p.strip() for p in str(finding.get("products") or "").split("\u00d7")]
        if len(parts) != 2 or not all(p in eligible for p in parts):
            continue
        pair = tuple(sorted(parts))
        if pair in seen:
            continue
        seen.add(pair)
        extra.append({
            "rule": "IMDG 7.2.6.5",
            "severity": "info",
            "message": pick(
                {
                    "nl": "Mogelijke uitzondering: stoffen van klasse 8, verpakkingsgroep "
                          "II of III, in colli tot 30 L of 30 kg hoeven onderling niet "
                          "gescheiden te worden, mits ze niet gevaarlijk met elkaar "
                          "reageren en het vervoersdocument de verklaring van "
                          "5.4.1.5.11.3 draagt. De scheidingsmelding hierboven blijft "
                          "staan; de beoordeling is aan de afzender.",
                    "en": "Possible exception: class 8 substances of packing group II or "
                          "III in packages up to 30 L or 30 kg need not be segregated "
                          "from one another, provided they do not react dangerously with "
                          "each other and the transport document carries the "
                          "5.4.1.5.11.3 statement. The segregation finding above stands; "
                          "the judgement rests with the shipper.",
                    "de": "Mögliche Ausnahme: Stoffe der Klasse 8, Verpackungsgruppe II "
                          "oder III, in Versandstücken bis 30 L oder 30 kg müssen "
                          "untereinander nicht getrennt werden, sofern sie nicht "
                          "gefährlich miteinander reagieren und das Beförderungspapier "
                          "die Erklärung nach 5.4.1.5.11.3 trägt. Der Trennhinweis oben "
                          "bleibt bestehen; die Beurteilung liegt beim Versender.",
                },
                lang,
            ),
            "products": "  \u00d7  ".join(pair),
        })
    return findings + extra


def check_imdg_amendment_42_24(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """Wat Amendment 42-24 aan de gedeclareerde stoffen verandert.

    De stof-specifieke IMDG-laag komt van de UN-kaarten van 41-22, terwijl de
    basisclassificatie uit ADR 2025 komt. Waar 42-24 daarvan afwijkt, moet dat
    bij de zending staan en niet alleen in de documentatie.

    De classificatie wordt niet stilzwijgend overschreven. Wijzigt 42-24 de
    klasse, het nevengevaar of de verpakkingsgroep, dan is de scheiding die de
    app berekent op de oude classificatie gebaseerd, en dat wordt met zoveel
    woorden gezegd. Een aangepaste klasse binnensmonds toepassen zou de uitkomst
    veranderen zonder dat iemand kan zien waarom.
    """
    lang = _lang(language)
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for entry, index, product in _iter_products(entries):
        un = str(product.get("un_number") or "").strip()
        if not un:
            continue
        label = _product_label(entry, product, index)
        pg = str(product.get("packing_group") or "").strip().upper()
        overlay = amendment_42_24.overlay_for(un, pg)

        for line in amendment_42_24.changes_for(un, pg, lang):
            key = (label, line)
            if key in seen:
                continue
            seen.add(key)
            findings.append({
                "rule": f"IMDG {amendment_42_24.amendment()}",
                "severity": "info",
                "message": line,
                "products": label,
            })

        reclassified = {"class", "subsidiary_risks_add", "packing_group"} & set(overlay)
        if reclassified:
            findings.append({
                "rule": f"IMDG {amendment_42_24.amendment()} — " + pick(
                    {
                        "nl": "classificatie",
                        "en": "classification",
                        "de": "Klassifizierung",
                    },
                    lang,
                ),
                "severity": "warning",
                "message": pick(
                    {
                        "nl": "De classificatie van deze stof is in 42-24 gewijzigd. De app "
                              "rekent de scheiding door op de classificatie van ADR Tabel A "
                              "en past die niet vanzelf aan; controleer de uitkomst tegen de "
                              "vermelding in de Dangerous Goods List van 42-24.",
                        "en": "The classification of this substance changed in 42-24. The app "
                              "computes segregation on the ADR Table A classification and does "
                              "not adjust it automatically; check the outcome against the "
                              "42-24 Dangerous Goods List entry.",
                        "de": "Die Klassifizierung dieses Stoffes hat sich in 42-24 geändert. "
                              "Die App berechnet die Trennung anhand der Klassifizierung nach "
                              "ADR Tabelle A und passt sie nicht selbsttätig an; prüfen Sie "
                              "das Ergebnis gegen den Eintrag in der Dangerous Goods List von "
                              "42-24.",
                    },
                    lang,
                ),
                "products": label,
            })

        requirement = amendment_42_24.document_requirement(un, lang)
        if requirement:
            findings.append({
                "rule": f"IMDG {requirement['section']}",
                "severity": "warning",
                "message": requirement["text"],
                "products": label,
            })
    return findings


# Divisies die in de luchtvaart (vrijwel altijd) verboden zijn; de ICAO TI
# vermeldt chloor en verwante 2.3-gassen als verboden op passagiers- én
# vrachttoestellen, met alleen een A1/A2-ontheffing als uitweg.
_AIR_FORBIDDEN_DIVISIONS = {"2.3"}


def check_air_forbidden(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """ICAO TI / IATA DGR: divisies die niet door de lucht mogen.

    De klassekolom van Tabel A zegt bij gassen alleen "2"; de divisie komt uit
    de etiketten. Daarom wordt hier zowel op de gevarentokens van het product
    als op de via parse_hazards opgeloste divisie getoetst — anders blijft
    chloor (UN 1017, klasse "2", etiket 2.3) onzichtbaar totdat /dg/prepare
    de divisie in het klasseveld heeft gezet.
    """
    lang = _lang(language)
    warnings: list[dict[str, Any]] = []
    for entry, index, product in _iter_products(entries):
        tokens = {t.lower() for t in _hazard_tokens(product)}
        division = str(parse_hazards(product).get("division") or "").strip().lower()
        if division:
            tokens.add(division)
        if not tokens & {d.lower() for d in _AIR_FORBIDDEN_DIVISIONS}:
            continue
        warnings.append({
            "rule": "ICAO TI / IATA DGR — divisie 2.3",
            "severity": "error",
            "message": pick(
                {
                    "nl": "Divisie 2.3 (giftige gassen) is in de luchtvaart verboden op "
                          "passagiers- én vrachttoestellen, op enkele uitzonderingen na. "
                          "Vervoer is alleen mogelijk met een ontheffing of voorafgaande "
                          "goedkeuring van de betrokken autoriteiten (A1/A2).",
                    "en": "Division 2.3 (toxic gases) is forbidden in air transport on "
                          "passenger and cargo aircraft alike, with few exceptions. "
                          "Carriage is only possible under an exemption or prior approval "
                          "of the authorities concerned (A1/A2).",
                    "de": "Unterklasse 2.3 (giftige Gase) ist in der Luftbeförderung auf "
                          "Passagier- wie Frachtflugzeugen bis auf wenige Ausnahmen "
                          "verboten. Eine Beförderung ist nur mit einer Ausnahme oder "
                          "vorheriger Genehmigung der betroffenen Behörden möglich "
                          "(A1/A2).",
                },
                lang,
            ),
            "products": _product_label(entry, product, index),
        })
    return warnings


def check_q_value(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """IATA 5.0.2.11: Q-waarde per positie voor 'all packed in one'.

    Gerekend met Decimal en zonder tussentijdse afronding: twee componenten van
    elk 0,50001 zijn samen 1,00002 en dus Q = 1,1 — overschreden. Eerst per
    component afronden maakte daar 1,0 van, een vals-negatieve uitkomst.

    Een component met ontbrekende, nul of negatieve waarden verdwijnt niet
    stilzwijgend: de positie krijgt status "incomplete" en de reden erbij.
    """
    rules = get_compliance_rules()["q_value"]
    lang = _lang(language)
    results: list[dict[str, Any]] = []

    for entry in entries:
        products = entry.get("products") or []
        # Een positie doet pas mee wanneer iemand een M (maximum per verpakking
        # volgens de packing instruction) heeft ingevuld. De n wordt door
        # /dg/prepare automatisch gevuld uit de netto per collo; alleen dáárop
        # afgaan zette elke luchtzending op "incomplete", ook waar 'all packed
        # in one' helemaal niet speelt.
        if not any(
            str(product.get("q_max_net_quantity") or "").strip()
            for product in products
        ):
            # Twee of meer stoffen op één positie zonder enige Q-invoer: dan
            # kán 'all packed in one' spelen en is er niets gerekend. Die
            # positie stilzwijgend overslaan liet de zending als "gecontroleerd"
            # gelden zodra één andere positie wél was ingevuld — een controle
            # die niet liep zag er dan uit als een controle die slaagde.
            if len([p for p in products if str(p.get("un_number") or "").strip()]) >= 2:
                results.append({
                    "position": entry.get("vehicle") or entry.get("line_id"),
                    "components": [],
                    "status": "not_checked",
                    "q_value": None,
                    "exceeded": None,
                    "note": pick(
                        {
                            "nl": "Geen Q berekend voor deze positie: er staan meer "
                                  "stoffen op één positie, maar n en M zijn niet "
                                  "ingevuld. Speelt 'all packed in one', vul ze dan in.",
                            "en": "No Q computed for this position: it holds more than "
                                  "one substance but n and M were not entered. If all "
                                  "packed in one applies, enter them.",
                            "de": "Kein Q für diese Position berechnet: sie enthält "
                                  "mehrere Stoffe, aber n und M wurden nicht angegeben. "
                                  "Falls All packed in one zutrifft, geben Sie sie an.",
                        },
                        lang,
                    ),
                })
            continue
        components: list[dict[str, Any]] = []
        invalid: list[str] = []
        for index, product in enumerate(entry.get("products") or []):
            raw_n = product.get("q_net_quantity")
            raw_m = product.get("q_max_net_quantity")
            participates = any(str(v or "").strip() for v in (raw_n, raw_m))
            if not participates:
                continue
            label = _product_label(entry, product, index)
            n = _num(raw_n)
            m = _num(raw_m)
            if n is None or m is None or n <= 0 or m <= 0:
                reason_nl = "ontbrekende, nul of negatieve n of M"
                reason_en = "missing, zero or negative n or M"
                invalid.append(f"{label} ({reason_nl if lang == 'nl' else reason_en})")
                continue
            ratio = Decimal(str(n)) / Decimal(str(m))
            components.append({
                "product": label,
                "net_quantity": n,
                "max_per_package": m,
                # Alleen voor weergave afgerond; de som gebruikt de ruwe ratio.
                "ratio": float(ratio.quantize(Decimal("0.0001"), rounding=ROUND_CEILING)),
                "_ratio_exact": ratio,
            })

        if not components and not invalid:
            continue

        if invalid:
            results.append({
                "position": entry.get("vehicle") or entry.get("line_id"),
                "components": [
                    {k: v for k, v in c.items() if k != "_ratio_exact"} for c in components
                ],
                "status": "incomplete",
                "q_value": None,
                "exceeded": None,
                "invalid_components": invalid,
                "note": pick(
                    {
                        "nl": "Q kan niet worden bepaald: ",
                        "en": "Q cannot be determined: ",
                        "de": "Q kann nicht bestimmt werden: ",
                    },
                    lang,
                ) + "; ".join(invalid),
            })
            continue

        if len(components) < 2:
            # Eén deelnemend product: geen 'all packed in one', geen Q nodig.
            continue

        q_raw = sum((c["_ratio_exact"] for c in components), Decimal(0))
        # Naar boven afronden op één decimaal, over de ongeronde som.
        q_rounded = float(q_raw.quantize(Decimal("0.1"), rounding=ROUND_CEILING))
        results.append({
            "position": entry.get("vehicle") or entry.get("line_id"),
            "components": [
                {k: v for k, v in c.items() if k != "_ratio_exact"} for c in components
            ],
            "status": "exceeded" if q_rounded > rules["limit"] else "ok",
            "q_value": q_rounded,
            "exceeded": q_rounded > rules["limit"],
            "note": pick(rules["note"], lang),
        })
    return results


# Massa in gram, volume in milliliter: de gemeenschappelijke noemer waarin de
# grenzen van 3.4 (kolom 7a) en 3.5.1.2 (E-codes) zijn uitgedrukt.
_Q_STATUS_MESSAGE = {
    "nl": {
        "checked": "De Q-controle is uitgevoerd voor de ingevoerde 'all packed in one'-gegevens.",
        "incomplete": "De Q-controle is niet volledig: vul voor iedere deelnemende stof n en M groter dan nul in.",
        "exceeded": "De berekende Q-waarde is groter dan 1.",
        "not_checked": "Geen Q-controle uitgevoerd. Is 'all packed in one' van toepassing, vul dan per stof de nettohoeveelheid n en de maximaal toegestane hoeveelheid M in.",
    },
    "en": {
        "checked": "The Q check was performed for the entered all-packed-in-one data.",
        "incomplete": "The Q check is incomplete: enter n and M greater than zero for every participating substance.",
        "exceeded": "The calculated Q value exceeds 1.",
        "not_checked": "No Q check was performed. If all packed in one applies, enter net quantity n and maximum permitted quantity M for each substance.",
    },
    "de": {
        "checked": "Die Q-Prüfung wurde für die eingegebenen All-packed-in-one-Daten durchgeführt.",
        "incomplete": "Die Q-Prüfung ist unvollständig: Geben Sie für jeden beteiligten Stoff n und M größer als null ein.",
        "exceeded": "Der berechnete Q-Wert ist größer als 1.",
        "not_checked": "Keine Q-Prüfung durchgeführt. Falls All packed in one zutrifft, geben Sie je Stoff die Nettomenge n und die höchstzulässige Menge M ein.",
    },
}


def q_check_status(q_values: list[dict[str, Any]], language: str = "nl") -> dict[str, str]:
    """Of de Q-controle liep, en zo niet, dat dat gezegd wordt.

    Een positie die stilzwijgend werd overgeslagen was op het scherm niet te
    onderscheiden van een positie die de toets haalde. Eén niet-gecontroleerde
    positie maakt de hele zending niet-gecontroleerd: "gecontroleerd" mag niet
    betekenen "één van de twee posities is gecontroleerd".
    """
    lang = _lang(language)
    statuses = {item.get("status") for item in q_values}
    if not q_values:
        status = "not_checked"
    elif "exceeded" in statuses:
        status = "exceeded"
    elif "incomplete" in statuses:
        status = "incomplete"
    elif "not_checked" in statuses:
        status = "not_checked"
    else:
        status = "checked"
    return {"status": status, "message": _Q_STATUS_MESSAGE[lang][status]}


_MEASURE_UNITS: dict[str, tuple[float, str]] = {
    "kg": (1000.0, "mass"),
    "g": (1.0, "mass"),
    "gr": (1.0, "mass"),
    "gram": (1.0, "mass"),
    "mg": (0.001, "mass"),
    "l": (1000.0, "volume"),
    "ltr": (1000.0, "volume"),
    "liter": (1000.0, "volume"),
    "litre": (1000.0, "volume"),
    "ml": (1.0, "volume"),
}

_MEASURE_RE = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*(kg|mg|gram|gr|g|ml|ltr|litre|liter|l)\b", re.IGNORECASE
)


def _parse_measures(value: Any) -> list[tuple[float, str]]:
    """Alle hoeveelheden met eenheid uit een tekst, in g of ml.

    '0,5 L' → [(500.0, 'volume')]; '500 ml oder 500 g' → beide. Een getal
    zonder eenheid levert niets op: '0,5' kan 0,5 g of 0,5 kg betekenen, en
    juist bij een vrijstellingsgrens mag daar niet naar geraden worden.
    """
    found: list[tuple[float, str]] = []
    for match in _MEASURE_RE.finditer(str(value or "")):
        amount = float(match.group(1).replace(",", "."))
        factor, kind = _MEASURE_UNITS[match.group(2).lower()]
        found.append((amount * factor, kind))
    return found


def _format_base(amount: float, kind: str) -> str:
    """500.0 → '500 ml' of '500 g'; 5000.0 → '5 L' of '5 kg'."""
    unit = "ml" if kind == "volume" else "g"
    if amount >= 1000 and amount % 1000 == 0:
        amount, unit = amount / 1000, "L" if kind == "volume" else "kg"
    text = str(int(amount)) if float(amount).is_integer() else f"{amount:g}"
    return f"{text} {unit}"


# Verwijzing naar een bijzondere bepaling in kolom 7a/7b ("siehe SV 340",
# "See SP277"): geen grens die de app kan toetsen.
_SPECIAL_PROVISION_REF = re.compile(r"\b(?:siehe|see)\b|\bS[VP]\s*\d+", re.IGNORECASE)

_LQ_MESSAGES = {
    "no_data": {
        "nl": "Geen LQ-waarde (kolom 7a) beschikbaar voor deze stof; niet getoetst.",
        "en": "No LQ value (column 7a) available for this substance; not assessed.",
        "de": "Kein LQ-Wert (Spalte 7a) für diesen Stoff verfügbar; nicht geprüft.",
    },
    "special_provision": {
        "nl": "Kolom 7a verwijst naar een bijzondere bepaling ({raw}); die tekst staat "
              "niet in CargoPilot. Raadpleeg hoofdstuk 3.3.",
        "en": "Column 7a refers to a special provision ({raw}); that text is not held "
              "by CargoPilot. Consult chapter 3.3.",
        "de": "Spalte 7a verweist auf eine Sondervorschrift ({raw}); dieser Text ist "
              "nicht in CargoPilot enthalten. Ziehen Sie Kapitel 3.3 heran.",
    },
    "not_permitted": {
        "nl": "Kolom 7a is '0': vervoer als gelimiteerde hoeveelheid (3.4) is voor "
              "deze stof niet toegestaan.",
        "en": "Column 7a is '0': carriage as limited quantity (3.4) is not permitted "
              "for this substance.",
        "de": "Spalte 7a ist '0': Die Beförderung als begrenzte Menge (3.4) ist für "
              "diesen Stoff nicht zugelassen.",
    },
    "missing_inner": {
        "nl": "LQ-grens {limit}: niet getoetst. Vul de netto hoeveelheid per "
              "binnenverpakking in, met eenheid (bijv. '500 g' of '0,5 L').",
        "en": "LQ limit {limit}: not assessed. Enter the net quantity per inner "
              "packaging, with a unit (e.g. '500 g' or '0.5 L').",
        "de": "LQ-Grenze {limit}: nicht geprüft. Geben Sie die Nettomenge je "
              "Innenverpackung mit Einheit an (z. B. '500 g' oder '0,5 L').",
    },
    "unit_mismatch": {
        "nl": "De eenheid van de binnenverpakking ({inner}) past niet bij de "
              "LQ-grens ({limit}): massa en volume zijn niet uitwisselbaar. "
              "Controleer de invoer.",
        "en": "The unit of the inner packaging ({inner}) does not match the LQ limit "
              "({limit}): mass and volume are not interchangeable. Check the input.",
        "de": "Die Einheit der Innenverpackung ({inner}) passt nicht zur LQ-Grenze "
              "({limit}): Masse und Volumen sind nicht austauschbar. Prüfen Sie die "
              "Eingabe.",
    },
    "inner_exceeded": {
        "nl": "De netto hoeveelheid per binnenverpakking ({inner}) is groter dan de "
              "LQ-grens van {limit}. Deze regel kan niet als gelimiteerde hoeveelheid "
              "(3.4) reizen en blijft volledig onder de voorschriften vallen.",
        "en": "The net quantity per inner packaging ({inner}) exceeds the LQ limit of "
              "{limit}. This line cannot travel as a limited quantity (3.4) and "
              "remains fully regulated.",
        "de": "Die Nettomenge je Innenverpackung ({inner}) überschreitet die LQ-Grenze "
              "von {limit}. Diese Zeile kann nicht als begrenzte Menge (3.4) befördert "
              "werden und unterliegt weiterhin allen Vorschriften.",
    },
    "missing_gross": {
        "nl": "Binnenverpakking ({inner}) ≤ LQ-grens {limit}. Vul de bruto massa per "
              "collo in om ook de grens van 30 kg (3.4.2) te toetsen.",
        "en": "Inner packaging ({inner}) ≤ LQ limit {limit}. Enter the gross mass per "
              "package to also assess the 30 kg limit (3.4.2).",
        "de": "Innenverpackung ({inner}) ≤ LQ-Grenze {limit}. Geben Sie die Bruttomasse "
              "je Versandstück an, um auch die 30-kg-Grenze (3.4.2) zu prüfen.",
    },
    "gross_exceeded": {
        "nl": "Binnenverpakking ({inner}) ≤ LQ-grens {limit}, maar de bruto massa per "
              "collo ({gross} kg) is groter dan de 30 kg van 3.4.2. Deze regel kan zo "
              "niet als gelimiteerde hoeveelheid reizen.",
        "en": "Inner packaging ({inner}) ≤ LQ limit {limit}, but the gross mass per "
              "package ({gross} kg) exceeds the 30 kg of 3.4.2. As packed, this line "
              "cannot travel as a limited quantity.",
        "de": "Innenverpackung ({inner}) ≤ LQ-Grenze {limit}, aber die Bruttomasse je "
              "Versandstück ({gross} kg) überschreitet die 30 kg nach 3.4.2. So "
              "verpackt kann diese Zeile nicht als begrenzte Menge befördert werden.",
    },
    "within_limits": {
        "nl": "Binnen de grenzen van 3.4: {inner} per binnenverpakking ≤ {limit} en "
              "{gross} kg bruto per collo ≤ 30 kg (voor trays met krimp- of rekfolie "
              "geldt 20 kg, 3.4.3). Het LQ-kenmerk en de verpakkingseisen van 3.4 "
              "blijven gelden.",
        "en": "Within the limits of 3.4: {inner} per inner packaging ≤ {limit} and "
              "{gross} kg gross per package ≤ 30 kg (20 kg for shrink- or "
              "stretch-wrapped trays, 3.4.3). The LQ mark and the packaging "
              "requirements of 3.4 still apply.",
        "de": "Innerhalb der Grenzen von 3.4: {inner} je Innenverpackung ≤ {limit} und "
              "{gross} kg brutto je Versandstück ≤ 30 kg (für Trays mit Schrumpf- "
              "oder Dehnfolie gelten 20 kg, 3.4.3). Die LQ-Kennzeichnung und die "
              "Verpackungsvorschriften von 3.4 gelten weiterhin.",
    },
}

# Alleen zinvol naast een puntentabel, dus alleen bij een landprofiel: een
# regel die daadwerkelijk als LQ reist, telt volgens 1.1.3.6.5 niet mee in de
# 1.1.3.6-punten. De tabel blijft hem meetellen — een vrijstelling neemt hier
# nooit stilzwijgend een uitkomst weg.
_LQ_POINTS_NOTE = {
    "nl": " Reist deze regel als LQ, dan telt hij volgens 1.1.3.6.5 niet mee in de "
          "1.1.3.6-punten; de puntentabel telt hem volledigheidshalve wél mee.",
    "en": " If this line travels as LQ it does not count towards the 1.1.3.6 points "
          "per 1.1.3.6.5; the points table still includes it for completeness.",
    "de": " Wird diese Zeile als LQ befördert, zählt sie nach 1.1.3.6.5 nicht zu den "
          "Punkten nach 1.1.3.6; die Punktetabelle führt sie der Vollständigkeit "
          "halber dennoch auf.",
}

_EQ_MESSAGES = {
    "no_data": {
        "nl": "Geen E-code (kolom 7b) beschikbaar voor deze stof; niet getoetst.",
        "en": "No E code (column 7b) available for this substance; not assessed.",
        "de": "Kein E-Code (Spalte 7b) für diesen Stoff verfügbar; nicht geprüft.",
    },
    "special_provision": {
        "nl": "Kolom 7b verwijst naar een bijzondere bepaling ({raw}); die tekst staat "
              "niet in CargoPilot. Raadpleeg hoofdstuk 3.3.",
        "en": "Column 7b refers to a special provision ({raw}); that text is not held "
              "by CargoPilot. Consult chapter 3.3.",
        "de": "Spalte 7b verweist auf eine Sondervorschrift ({raw}); dieser Text ist "
              "nicht in CargoPilot enthalten. Ziehen Sie Kapitel 3.3 heran.",
    },
    "not_permitted": {
        "nl": "E0: vervoer als vrijgestelde hoeveelheid (3.5) is voor deze stof niet "
              "toegestaan.",
        "en": "E0: carriage as excepted quantity (3.5) is not permitted for this "
              "substance.",
        "de": "E0: Die Beförderung als freigestellte Menge (3.5) ist für diesen Stoff "
              "nicht zugelassen.",
    },
    "missing_inner": {
        "nl": "{code} (max. {inner_cap} g/ml per binnenverpakking, {outer_cap} g/ml "
              "per collo): niet getoetst. Vul de netto hoeveelheid per "
              "binnenverpakking in, met eenheid.",
        "en": "{code} (max. {inner_cap} g/ml per inner packaging, {outer_cap} g/ml per "
              "package): not assessed. Enter the net quantity per inner packaging, "
              "with a unit.",
        "de": "{code} (max. {inner_cap} g/ml je Innenverpackung, {outer_cap} g/ml je "
              "Versandstück): nicht geprüft. Geben Sie die Nettomenge je "
              "Innenverpackung mit Einheit an.",
    },
    "missing_outer": {
        "nl": "{code}: binnenverpakking ({inner}) ≤ {inner_cap} g/ml. Vul de netto "
              "hoeveelheid per collo in (met eenheid) om ook de grens van {outer_cap} "
              "g/ml per buitenverpakking te toetsen.",
        "en": "{code}: inner packaging ({inner}) ≤ {inner_cap} g/ml. Enter the net "
              "quantity per package (with a unit) to also assess the {outer_cap} g/ml "
              "limit per outer packaging.",
        "de": "{code}: Innenverpackung ({inner}) ≤ {inner_cap} g/ml. Geben Sie die "
              "Nettomenge je Versandstück (mit Einheit) an, um auch die Grenze von "
              "{outer_cap} g/ml je Außenverpackung zu prüfen.",
    },
    "inner_exceeded": {
        "nl": "De netto hoeveelheid per binnenverpakking ({inner}) is groter dan de "
              "{inner_cap} g/ml van {code} (3.5.1.2). Deze regel kan niet als "
              "vrijgestelde hoeveelheid reizen.",
        "en": "The net quantity per inner packaging ({inner}) exceeds the {inner_cap} "
              "g/ml of {code} (3.5.1.2). This line cannot travel as an excepted "
              "quantity.",
        "de": "Die Nettomenge je Innenverpackung ({inner}) überschreitet die "
              "{inner_cap} g/ml von {code} (3.5.1.2). Diese Zeile kann nicht als "
              "freigestellte Menge befördert werden.",
    },
    "outer_exceeded": {
        "nl": "De netto hoeveelheid per collo ({outer}) is groter dan de {outer_cap} "
              "g/ml van {code} (3.5.1.2). Deze regel kan zo niet als vrijgestelde "
              "hoeveelheid reizen.",
        "en": "The net quantity per package ({outer}) exceeds the {outer_cap} g/ml of "
              "{code} (3.5.1.2). As packed, this line cannot travel as an excepted "
              "quantity.",
        "de": "Die Nettomenge je Versandstück ({outer}) überschreitet die {outer_cap} "
              "g/ml von {code} (3.5.1.2). So verpackt kann diese Zeile nicht als "
              "freigestellte Menge befördert werden.",
    },
    "within_limits": {
        "nl": "Binnen de grenzen van {code}: {inner} per binnenverpakking ≤ "
              "{inner_cap} g/ml en {outer} per collo ≤ {outer_cap} g/ml (3.5.1.2). De "
              "verpakkings- en beproevingseisen van 3.5.2 en 3.5.3 en het EQ-kenmerk "
              "blijven gelden; per voertuig of container zijn ten hoogste 1000 colli "
              "toegestaan (3.5.5).",
        "en": "Within the limits of {code}: {inner} per inner packaging ≤ {inner_cap} "
              "g/ml and {outer} per package ≤ {outer_cap} g/ml (3.5.1.2). The "
              "packaging and testing requirements of 3.5.2 and 3.5.3 and the EQ mark "
              "still apply; at most 1,000 packages are permitted per vehicle or "
              "container (3.5.5).",
        "de": "Innerhalb der Grenzen von {code}: {inner} je Innenverpackung ≤ "
              "{inner_cap} g/ml und {outer} je Versandstück ≤ {outer_cap} g/ml "
              "(3.5.1.2). Die Verpackungs- und Prüfvorschriften nach 3.5.2 und 3.5.3 "
              "sowie die EQ-Kennzeichnung gelten weiterhin; je Fahrzeug oder "
              "Container sind höchstens 1000 Versandstücke zulässig (3.5.5).",
    },
}

# ADR 3.4.2 / IMDG 3.4.2.1: totale bruto massa van een LQ-collo.
_LQ_GROSS_LIMIT_KG = 30.0
# ADR/IMDG 3.5.5: ten hoogste 1000 EQ-colli per voertuig of container.
_EQ_PACKAGE_CAP = 1000


def _fmt_kg(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _assess_lq(
    raw: str, inner: list[tuple[float, str]], gross_kg: float | None, lang: str
) -> dict[str, Any]:
    """Toets één regel aan kolom 7a en de 30 kg-grens van 3.4.2."""
    raw = raw.strip()
    result: dict[str, Any] = {"value": raw or None}

    def outcome(status: str, message_key: str, **kwargs: Any) -> dict[str, Any]:
        result["status"] = status
        result["message"] = pick(_LQ_MESSAGES[message_key], lang).format(**kwargs)
        return result

    if not raw or raw in {"-", "–", "—"} or "VERBOTEN" in raw.upper():
        return outcome("no_data", "no_data")
    if _num(raw) == 0:
        return outcome("not_permitted", "not_permitted")
    limits = _parse_measures(raw)
    if not limits:
        if _SPECIAL_PROVISION_REF.search(raw):
            return outcome("no_data", "special_provision", raw=raw)
        return outcome("no_data", "no_data")

    if not inner:
        return outcome("incomplete", "missing_inner", limit=raw)
    inner_amount, inner_kind = inner[0]
    # "500 ml oder 500 g": de variant die bij de ingevoerde eenheid hoort telt.
    limit = next(((a, k) for a, k in limits if k == inner_kind), None)
    if limit is None:
        return outcome(
            "incomplete", "unit_mismatch",
            inner=_format_base(inner_amount, inner_kind), limit=raw,
        )
    if inner_amount > limit[0]:
        return outcome(
            "not_within", "inner_exceeded",
            inner=_format_base(inner_amount, inner_kind), limit=raw,
        )
    if gross_kg is None:
        return outcome(
            "incomplete", "missing_gross",
            inner=_format_base(inner_amount, inner_kind), limit=raw,
        )
    if gross_kg > _LQ_GROSS_LIMIT_KG:
        return outcome(
            "not_within", "gross_exceeded",
            inner=_format_base(inner_amount, inner_kind), limit=raw,
            gross=_fmt_kg(gross_kg),
        )
    return outcome(
        "within_limits", "within_limits",
        inner=_format_base(inner_amount, inner_kind), limit=raw,
        gross=_fmt_kg(gross_kg),
    )


def _assess_eq(
    raw: str,
    inner: list[tuple[float, str]],
    outer: list[tuple[float, str]],
    lang: str,
) -> dict[str, Any]:
    """Toets één regel aan de E-code van kolom 7b (tabel 3.5.1.2)."""
    code = raw.strip().upper()
    result: dict[str, Any] = {"code": code or None}

    def outcome(status: str, message_key: str, **kwargs: Any) -> dict[str, Any]:
        result["status"] = status
        result["message"] = pick(_EQ_MESSAGES[message_key], lang).format(**kwargs)
        return result

    if not code or code in {"-", "–", "—"} or "VERBOTEN" in code:
        return outcome("no_data", "no_data")
    if code == "E0":
        return outcome("not_permitted", "not_permitted")
    caps = EXCEPTED_QUANTITY_LIMITS.get(code)
    if not caps:
        if _SPECIAL_PROVISION_REF.search(raw):
            return outcome("no_data", "special_provision", raw=raw.strip())
        return outcome("no_data", "no_data")
    inner_cap, outer_cap = caps

    # Tabel 3.5.1.2 telt in gram voor vaste stoffen en ml voor vloeistoffen en
    # gassen met hetzelfde getal; massa en volume delen hier dus één grens.
    if not inner:
        return outcome(
            "incomplete", "missing_inner",
            code=code, inner_cap=inner_cap, outer_cap=outer_cap,
        )
    inner_amount, inner_kind = inner[0]
    if inner_amount > inner_cap:
        return outcome(
            "not_within", "inner_exceeded",
            inner=_format_base(inner_amount, inner_kind), inner_cap=inner_cap, code=code,
        )
    if not outer:
        return outcome(
            "incomplete", "missing_outer",
            code=code, inner=_format_base(inner_amount, inner_kind),
            inner_cap=inner_cap, outer_cap=outer_cap,
        )
    outer_amount, outer_kind = outer[0]
    if outer_amount > outer_cap:
        return outcome(
            "not_within", "outer_exceeded",
            outer=_format_base(outer_amount, outer_kind), outer_cap=outer_cap, code=code,
        )
    return outcome(
        "within_limits", "within_limits",
        code=code,
        inner=_format_base(inner_amount, inner_kind), inner_cap=inner_cap,
        outer=_format_base(outer_amount, outer_kind), outer_cap=outer_cap,
    )


def check_lq_eq(
    entries: list[dict[str, Any]], language: str = "nl", profiles: list[str] | None = None
) -> dict[str, Any]:
    """ADR/IMDG 3.4 en 3.5: toets de ingevoerde hoeveelheden aan kolom 7a en 7b.

    Tot nu toe werden de LQ-waarde en de E-code getoond met hun betekenis, maar
    nooit vergeleken met wat er daadwerkelijk is ingevuld. Deze controle doet
    die vergelijking — en niet meer dan dat. Kwalificeren op hoeveelheid is
    niet hetzelfde als vrijgesteld zijn: het kenmerk, de verpakkingseisen en de
    beproevingen van 3.4 en 3.5 blijven bij de afzender. Daarom wordt een regel
    die binnen de grenzen valt gemeld en nooit stilzwijgend uit de
    puntenberekening van 1.1.3.6 gehaald, precies zoals de vrijstelling van
    IMDG 7.2.6.3 wordt gemeld zonder een waarschuwing weg te nemen.
    """
    lang = _lang(language)
    normalized = sorted({p.upper() for p in (profiles or [])})
    use_imdg = "IMDG" in normalized

    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    statuses: set[str] = set()
    # ADR 3.4.13/3.4.14: boven 8 ton bruto aan LQ-colli per transporteenheid is
    # de LQ-kenmerking van 3.4.15 op de eenheid vereist. De zending wordt hier
    # als één transporteenheid gelezen — meer weet de app niet van het voertuig.
    lq_gross_total_kg = 0.0
    lq_gross_products: list[str] = []

    for entry in entries:
        eq_packages = 0.0
        eq_products: list[str] = []
        for index, product in enumerate(entry.get("products") or []):
            un = str(product.get("un_number") or "").strip()
            lq_raw = str(product.get("limited_quantity") or "").strip()
            eq_raw = str(product.get("excepted_quantity") or "").strip()
            if not un and not lq_raw and not eq_raw:
                continue
            if product.get("transport_forbidden"):
                # Geen vrijstellingsroute voor een stof die niet ten vervoer
                # mag worden aangeboden; het verbod staat al in beeld.
                continue
            label = _product_label(entry, product, index)

            # De IMDG-lijst (42-24) draagt dezelfde kolommen. Waar het product
            # geen waarde heeft, vult de lijst hem aan; waar de waarden
            # verschillen, wordt dat gemeld — de toets rekent met de ingevoerde
            # waarde en beslist niet zelf welke editie voorgaat.
            dgl_notes = {"limited_quantity": "", "excepted_quantity": ""}
            if use_imdg and un:
                dgl_row = dangerous_goods_list.entry_for(
                    un, str(product.get("packing_group") or "")
                )
                for column, current in (("limited_quantity", lq_raw),
                                        ("excepted_quantity", eq_raw)):
                    dgl_value = dangerous_goods_list.value(dgl_row, column)
                    if not dgl_value:
                        continue
                    if not current:
                        if column == "limited_quantity":
                            lq_raw = dgl_value
                        else:
                            eq_raw = dgl_value
                    elif dgl_value.replace(" ", "").upper() != current.replace(" ", "").upper():
                        dgl_notes[column] = " " + pick(
                            {
                                "nl": "Let op: de IMDG-lijst (42-24) vermeldt hier "
                                      "{value}; controleer welke waarde voor het "
                                      "zeetraject geldt.",
                                "en": "Note: the IMDG list (42-24) states {value} "
                                      "here; check which value applies to the sea "
                                      "leg.",
                                "de": "Hinweis: die IMDG-Liste (42-24) nennt hier "
                                      "{value}; prüfen Sie, welcher Wert für die "
                                      "Seestrecke gilt.",
                            },
                            lang,
                        ).format(value=dgl_value)

            inner = _parse_measures(product.get("net_per_inner_packaging"))
            outer = _parse_measures(product.get("net_mass_liters_per_package"))
            gross_measures = _parse_measures(product.get("gross_mass_per_package"))
            if gross_measures and gross_measures[0][1] == "mass":
                gross_kg: float | None = gross_measures[0][0] / 1000.0
            else:
                gross_kg = _num(product.get("gross_mass_per_package"))

            lq = _assess_lq(lq_raw, inner, gross_kg, lang)
            eq = _assess_eq(eq_raw, inner, outer, lang)
            if lq["status"] == "within_limits" and {"ADR", "RID", "ADN"} & set(normalized):
                lq["message"] += pick(_LQ_POINTS_NOTE, lang)
            lq["message"] += dgl_notes["limited_quantity"]
            eq["message"] += dgl_notes["excepted_quantity"]
            statuses.add(lq["status"])
            statuses.add(eq["status"])
            rows.append({
                "product": label,
                "position": entry.get("vehicle") or entry.get("line_id"),
                "lq": lq,
                "eq": eq,
            })

            if eq["status"] == "within_limits":
                count = _num(product.get("quantity_packages"))
                if count:
                    eq_packages += count
                    eq_products.append(label)

            if lq["status"] == "within_limits" and gross_kg:
                count = _num(product.get("quantity_packages"))
                if count:
                    lq_gross_total_kg += gross_kg * count
                    lq_gross_products.append(label)

        if eq_packages > _EQ_PACKAGE_CAP:
            warnings.append({
                "rule": "ADR/IMDG 3.5.5",
                "severity": "warning",
                "message": pick(
                    {
                        "nl": "Deze positie telt {count} colli die binnen de "
                              "EQ-grenzen vallen; per voertuig of container zijn ten "
                              "hoogste 1000 colli met vrijgestelde hoeveelheden "
                              "toegestaan (3.5.5).",
                        "en": "This position counts {count} packages within the EQ "
                              "limits; at most 1,000 packages of excepted quantities "
                              "are permitted per vehicle or container (3.5.5).",
                        "de": "Diese Position zählt {count} Versandstücke innerhalb "
                              "der EQ-Grenzen; je Fahrzeug oder Container sind "
                              "höchstens 1000 Versandstücke mit freigestellten Mengen "
                              "zulässig (3.5.5).",
                    },
                    lang,
                ).format(count=_fmt_kg(eq_packages)),
                "products": ", ".join(eq_products),
            })

    if lq_gross_total_kg > 8000 and {"ADR", "RID", "ADN"} & set(normalized):
        warnings.append({
            "rule": "ADR 3.4.13/3.4.14",
            "severity": "warning",
            "message": pick(
                {
                    "nl": "De colli die binnen de LQ-grenzen vallen tellen samen "
                          "{tonnes} kg bruto. Boven 8 ton per transporteenheid is de "
                          "LQ-kenmerking van 3.4.15 (250 × 250 mm) op de voor- en "
                          "achterzijde vereist (3.4.13); de vrijstelling van 3.4.14 "
                          "geldt dan niet meer.",
                    "en": "The packages within the LQ limits total {tonnes} kg gross. "
                          "Above 8 tonnes per transport unit the LQ mark of 3.4.15 "
                          "(250 × 250 mm) is required at the front and rear (3.4.13); "
                          "the waiver of 3.4.14 no longer applies.",
                    "de": "Die Versandstücke innerhalb der LQ-Grenzen wiegen zusammen "
                          "{tonnes} kg brutto. Über 8 Tonnen je Beförderungseinheit ist "
                          "die LQ-Kennzeichnung nach 3.4.15 (250 × 250 mm) vorn und "
                          "hinten vorgeschrieben (3.4.13); die Erleichterung nach "
                          "3.4.14 gilt dann nicht mehr.",
                },
                lang,
            ).format(tonnes=_fmt_kg(lq_gross_total_kg)),
            "products": ", ".join(lq_gross_products),
        })

    if not rows:
        status = "not_checked"
    elif "incomplete" in statuses:
        status = "incomplete"
    else:
        status = "checked"

    basis = "ADR 3.4 / 3.5 (Tabel A kolom 7a/7b)"
    if use_imdg:
        basis += " + IMDG DGL 42-24"
    return {
        "rows": rows,
        "status": status,
        "warnings": warnings,
        "basis": basis,
        "basis_note": basis_note(normalized, "3.4/3.5", language),
        "note": pick(
            {
                "nl": "Binnen de grenzen vallen is niet hetzelfde als vrijgesteld "
                      "zijn: het LQ- of EQ-kenmerk en de verpakkingseisen van 3.4 en "
                      "3.5 blijven voorwaarden. De puntentelling van 1.1.3.6 wordt "
                      "hier niet door aangepast.",
                "en": "Falling within the limits is not the same as being exempt: "
                      "the LQ or EQ mark and the packaging requirements of 3.4 and "
                      "3.5 remain conditions. The 1.1.3.6 points calculation is not "
                      "adjusted by this result.",
                "de": "Innerhalb der Grenzen zu liegen ist nicht dasselbe wie "
                      "freigestellt zu sein: die LQ- bzw. EQ-Kennzeichnung und die "
                      "Verpackungsvorschriften von 3.4 und 3.5 bleiben Bedingungen. "
                      "Die Punkteberechnung nach 1.1.3.6 wird durch dieses Ergebnis "
                      "nicht verändert.",
            },
            lang,
        ),
    }


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
        # Welke regelgevingsedities dit resultaat heeft gebruikt. De tabellen van
        # hoofdstuk 7.2 zijn onder 42-24 ongewijzigd gebleven; de stof-specifieke
        # laag komt van 41-22 met de 42-24-verschillen eroverheen. Wat die laag
        # niet dekt, staat in IMDG_42_24_not_covered.
        "rule_sets": {
            "ADR": "ADR 2025 (Tabel A via rkstgr/adr-substances)",
            "IMDG_class_tables": (
                "Amendment 40-20 (hoofdstuk 7.2) — in 42-24 ongewijzigd voor "
                + ", ".join(amendment_42_24.verified_unchanged_sections())
            ),
            "IMDG_dangerous_goods_list": (
                f"Amendment 42-24, hoofdstuk 3.2 — "
                f"{dangerous_goods_list.source().get('entries', 0)} vermeldingen; "
                "kolom 16a en 16b komen hiervandaan"
            ),
            "IMDG_per_substance": (
                "Amendment 41-22 (Cantell UN-kaarten, 2023) met de verschillenlaag 42-24 "
                "— nog alleen voor marine pollutant en bulkvervoer"
            ),
            "IMDG_current_mandatory": (
                "Amendment 42-24, verplicht sinds 1-1-2026 — verschillenlaag toegepast; "
                "de gepubliceerde tekst blijft leidend"
            ),
            "IMDG_42_24_source": amendment_42_24.source(),
            "IMDG_42_24_not_covered": amendment_42_24.not_covered(_lang(language)),
            "EmS": "MSC.1/Circ.1588/Rev.3, aangevuld met de EmS-vermeldingen van 42-24",
            "IATA": "IATA DGR (lithium/natrium-ion: Guidance 2026)",
        },
    }
    normalized = {p.upper() for p in profiles}

    # Waar deze uitkomst mee is gerekend, in één id — bruikbaar in een melding
    # en in de controlebijlage bij een export.
    result["regulatory_manifest"] = summary()

    # Een regelset die is afgelopen en niet is vervangen, is geen detail: dan
    # rekent deze controle met tekst die niet meer geldt. De uitkomst blijft
    # staan, maar zegt er zelf bij dat hij op verlopen regels berust.
    for stale in stale_rule_sets(sorted(normalized)):
        result.setdefault("rule_set_warnings", []).append({
            "rule": stale["name"],
            "severity": "warning",
            "message": pick(
                {
                    "nl": "{edition} is verlopen op {on}. Deze controle rekent met een "
                          "editie die niet meer geldt; werk CargoPilot bij of raadpleeg de "
                          "actuele uitgave.",
                    "en": "{edition} expired on {on}. This check is computing with an "
                          "edition that no longer applies; update CargoPilot or consult the "
                          "current edition.",
                    "de": "{edition} ist am {on} abgelaufen. Diese Prüfung rechnet mit einer "
                          "Ausgabe, die nicht mehr gilt; aktualisieren Sie CargoPilot oder "
                          "ziehen Sie die geltende Ausgabe heran.",
                },
                language,
            ).format(edition=stale["edition"], on=stale["expired_on"]),
            "products": ", ".join(stale["profiles"]),
        })

    if {"ADR", "RID", "ADN"} & normalized:
        land = sorted({"ADR", "RID", "ADN"} & normalized)
        result["adr_points"] = check_adr_points(entries, language, land)
        result["adr_mixed_loading"] = check_adr_mixed_loading(entries, language, land)
        # ADN answers the exemption question with its own rule, so it gets its
        # own result rather than borrowing the points total.
        if "ADN" in normalized:
            result["adn_exemption"] = check_adn_exemption(entries, language)
        note = basis_note(land, "7.5.2", language)
        if note:
            result["adr_mixed_loading_basis_note"] = note

    # LQ/EQ geldt voor de landmodi én de zeevaart; de lucht kent met de
    # Y-verpakkingsinstructies een eigen stelsel dat hier niet wordt geclaimd.
    if {"ADR", "RID", "ADN", "IMDG"} & normalized:
        result["lq_eq"] = check_lq_eq(entries, language, sorted(normalized))

    if "IMDG" in normalized:
        result["imdg_segregation"] = append_class8_pair_exception(
            entries,
            apply_column_16b_precedence(
                check_imdg_segregation(entries, language)
                + check_imdg_class1_compatibility(entries, language)
                + check_imdg_segregation_groups(entries, language)
                + check_imdg_segregation_provisions(entries, language)
                + check_imdg_segregation_exemptions(entries, language),
                language,
            ),
            language,
        ) + check_imdg_amendment_42_24(entries, language)
        result["imdg_note"] = pick(rules["imdg_segregation"]["note"], language)
        groups = rules.get("imdg_segregation_groups")
        if groups:
            lang = _lang(language)
            result["imdg_segregation_groups"] = {
                "note": pick(groups["note"], lang),
                "class8_exception": pick(groups["class8_exception"], lang),
                "groups": [
                    {"code": item["code"], "label": pick(item, lang)} for item in groups["groups"]
                ],
            }

    if "IATA_DGR" in normalized:
        result["iata_segregation"] = (
            check_air_forbidden(entries, language)
            + check_iata_segregation(entries, language)
        )
        result["q_values"] = check_q_value(entries, language)
        # Of de Q-controle daadwerkelijk liep, hoort bij de uitkomst en niet bij
        # één endpoint. Tot v1.32.0 werd dit in de route berekend, waardoor het
        # paneel "geen Q-controle uitgevoerd" meldde en de export er niets over
        # zei — precies de plek waar het document de deur uit gaat. De
        # exportcontrole in exporter.py schrijft zelf dat het scherm nooit de
        # enige plek mag zijn waar dit wordt afgedwongen.
        result["q_check_status"] = q_check_status(result["q_values"], language)
        cao = [
            _product_label(entry, product, index)
            for entry, index, product in _iter_products(entries)
            if str(product.get("cargo_aircraft_only") or "").strip().upper() in {"Y", "YES", "JA", "TRUE", "1"}
        ]
        result["cargo_aircraft_only_products"] = cao

    return result
