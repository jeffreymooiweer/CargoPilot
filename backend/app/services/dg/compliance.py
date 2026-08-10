"""Compliance checks for dangerous goods: ADR 1.1.3.6 points, ADR 7.5.2 mixed
loading, the LQ/EQ limits of chapters 3.4 and 3.5, and IATA Table 9.3.A
segregation plus the Q value (5.0.2.11).

The results are guidance and warnings — not a legal determination. The
qualified person remains responsible (see DISCLAIMER.md).
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
    """Parse the first number out of a value ('333', '5 kg', '12,5 L').

    The sign counts: '-5 L' is -5, not 5. A negative quantity has to surface as
    an error rather than being silently made positive.
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
    """Every hazard class of a product: primary hazard plus subsidiary risks."""
    tokens: list[str] = []
    for raw in [product.get("class"), product.get("subsidiary_risks")]:
        for token in re.split(r"[,;/\s()+]+", str(raw or "")):
            token = token.strip().upper()
            if token:
                tokens.append(token)
    return tokens


def _is_class1(token: str) -> bool:
    return bool(re.match(r"^1(\.\d)?[A-S]?$", token)) and not token.startswith(("1.4S",))


def _compat_group(product: dict[str, Any]) -> str | None:
    """Compatibility group of a class 1 product (1.4G → 'G', for instance).

    The group lives in Table A in the classification code, not in the class
    column: for explosives that column only says "1". Hence the classification
    code is read first. Until v1.40.1 the ADR side looked only at the class
    field with a tight anchor, so 7.5.2.2 did not fire the moment the division
    did not happen to be in there.
    """
    for raw in (product.get("classification_code"), product.get("class"), product.get("subsidiary_risks")):
        match = re.search(r"\b1\.\d\s*([A-HJ-NPS])\b", str(raw or "").upper())
        if match:
            return match.group(1)
    return None


def _matches_iata_key(token: str, key: str) -> bool:
    """Match a hazard token against a 9.3.A key ('1', '2.1', '4.3', …)."""
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


#: The road, rail and inland waterway regimes each have a 1.1.3.6 and a mixed
#: loading chapter, but they are not the same texts. CargoPilot carries the ADR
#: tables; those of RID and ADN are not in it. Presenting that silently as a
#: "RID result" gives the user a certainty that does not exist, so the basis is
#: named the moment it differs from the chosen profile.
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
          "Anhaltspunkt und prüfen Sie es an dem für Ihre Strecke geltenden Text.", "fr": "Calculé avec les tableaux de l'ADR. Le {other} possède son propre {section}, dont CargoPilot ne dispose pas. Prenez ce résultat à titre indicatif et vérifiez-le dans le texte applicable à votre trajet."}

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
          "das ADR je Beförderungseinheit.", "fr": "Les 1.1.3.6.3 et 1.1.3.6.4 du RID prescrivent les mêmes catégories de transport, les mêmes facteurs (50, 3 et 1) et la même valeur calculée de 1000 que l'ADR. La différence tient à l'unité : le RID compte par wagon ou grand conteneur, l'ADR par unité de transport."}

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
          "das ADN-Ergebnis wird im Panel gesondert ausgewiesen.", "fr": "Attention : l'ADN ne connaît pas de calcul de points. Le 1.1.3.6.1 de l'ADN exempte sur la masse brute totale (3 000 kg au plus) et sur une limite propre à chaque classe. Ces points valent pour le trajet routier ; le résultat ADN est présenté séparément dans le panneau."}


def basis_note(profiles: list[str] | None, section: str, language: str) -> str | None:
    """A note for when an ADR table is used for RID or ADN.

    For 1.1.3.6 the basis has since been read in the official texts and no
    longer needs hedging: RID computes the same way, ADN computes something
    entirely different. For the remaining chapters the old, cautious note still
    stands — those have not been read yet.
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
    """ADR 1.1.3.6: points per product, total and exemption status."""
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
        # A substance that is forbidden for transport does not belong in the
        # points total: there is nothing to exempt, and "fill in the category"
        # next to the red prohibition is confusing. The line is named separately.
        if product.get("transport_forbidden"):
            forbidden.append(label)
            continue
        category = str(product.get("transport_category") or "").strip()
        quantity = _num(product.get("adr_total_quantity"))
        if category not in categories or quantity is None or quantity <= 0:
            # Zero or negative is unusable too: -5 L would lower the points
            # total and suggest an exemption that does not exist.
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
    """ADN 1.1.3.6.1: exemption for carriage in packages on board a vessel.

    ADN has no points count. It exempts when the gross mass of all dangerous
    goods together stays below 3000 kg *and* no single class exceeds its own
    limit — 0, 300 or 3000 kg, depending on packing group, group or label. For
    carriage in tanks the exemption does not apply at all.

    Until v1.32.0 an ADN consignment was shown the ADR points count. That is not
    an approximation of this answer but an answer to a different question: 1200
    kg of a liquid in packing group III costs 1200 ADR points and loses the
    exemption there, while ADN exempts the same consignment as long as the total
    stays under 3000 kg.
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
                      "weiter.", "fr": "L'ADN exempte sur la masse brute et non sur des points : le total reste inférieur à 3 000 kg et aucune classe ne dépasse sa propre limite. Le transport en citerne n'est jamais exempté. Les conditions du 1.1.3.6.2 restent applicables."},
            lang,
        ),
    }


def _mixed_loading_footnote(
    class1_un: str, other_un: str, other_class: str, footnotes: dict[str, Any]
) -> str | None:
    """Which footnote to table 7.5.2.1 permits this pair, if any.

    The cell for class 1 against another class is empty in the table —
    forbidden — except where a letter appears. Three of those matter here, and
    all three hang on the UN number rather than the class:

    (b) class 1 with life-saving appliances of class 9;
    (c) UN 0503 with UN 3268;
    (d) explosive with ammonium nitrate and related nitrates.

    Footnote (a) is there too, but it concerns 1.4S and that is already caught
    above: 1.4S does not count as class 1 for this table.
    """
    note_d = footnotes["d"]
    if (
        class1_un in note_d["blasting_explosive_un_numbers"]
        and class1_un not in note_d["excluded_un_numbers"]
        and other_un in note_d["nitrate_un_numbers"]
    ):
        return "d"
    if class1_un == footnotes["c"]["class1_un"] and other_un == footnotes["c"]["class9_un"]:
        return "c"
    if other_class.startswith("9") and other_un in footnotes["b"]["life_saving_un_numbers"]:
        return "b"
    return None


def _compatibility_table(profiles: list[str] | None) -> tuple[dict[str, Any], str]:
    """Which 7.5.2.2 table applies, and under which name it is cited.

    RID has its own 7.5.2.2 and it is not the same as the ADR one: it is missing
    compatibility group A. That is a difference in what the table answers, not
    in the answer — hence a rail leg gets the rail table and not the road one.
    ADN has no table of its own; that keeps borrowing, with the basis note that
    is already there.
    """
    compatibility = get_compliance_rules()["adr_mixed_loading"]["compatibility"]
    active = {p.upper() for p in (profiles or [])}
    if active == {"RID"}:
        return compatibility["rail"], "RID"
    return compatibility["road"], "ADR"


def _class1_compatibility(
    compat_groups: dict[str, list[str]],
    unknown: list[str],
    language: str,
    profiles: list[str] | None,
) -> list[dict[str, str]]:
    """ADR/RID 7.5.2.2: may this compatibility group travel next to that one?

    The table sets group against group. An empty cell is a prohibition, an X is
    "mixed loading permitted", and four cells carry a letter: then it is allowed,
    but not without conditions. Until v1.41.0 CargoPilot only counted the groups
    and handed the question back to the user; now the table is read.
    """
    rules = get_compliance_rules()["adr_mixed_loading"]["rules"]
    table, regime = _compatibility_table(profiles)
    order: list[str] = table["group_order"]
    matrix: dict[str, list[str]] = table["matrix"]
    lang = _lang(language)
    findings: list[dict[str, str]] = []

    known = sorted(g for g in compat_groups if g in order)
    outside = sorted(g for g in compat_groups if g not in order)

    for i, group_a in enumerate(known):
        for group_b in known[i:]:
            # On the diagonal this is about two packages of the same group; with
            # a single package there is nothing to load together.
            if group_a == group_b and len(compat_groups[group_a]) < 2:
                continue
            cell = matrix[group_a][order.index(group_b)]
            if cell == "X":
                continue
            products = ", ".join(
                dict.fromkeys(compat_groups[group_a] + compat_groups[group_b])
            )
            pair = f"{group_a} × {group_b}"
            if not cell:
                key = "class1_compat_forbidden_rail" if regime == "RID" else "class1_compat_forbidden"
                findings.append({
                    "rule": f"{regime} 7.5.2.2 ({pair})",
                    "severity": "error",
                    "message": pick(rules[key], lang).replace("{groups}", pair),
                    "products": products,
                })
                continue
            # A cell can refer to two footnotes ("b c"); then both apply and the
            # user should see both.
            for letter in cell:
                findings.append({
                    "rule": f"{regime} 7.5.2.2 ({pair}) ({letter})",
                    "severity": "warning",
                    "message": pick(rules[f"class1_compat_note_{letter}"], lang),
                    "products": products,
                })

    for group in outside:
        # What the table does not know, the table does not answer. Saying so is
        # the only honest option: group A *is* in ADR and is not in RID.
        findings.append({
            "rule": f"{regime} 7.5.2.2",
            "severity": "warning",
            "message": pick(rules["class1_compat_not_in_table"], lang)
            .replace("{group}", group)
            .replace("{regime}", regime)
            .replace("{products}", ", ".join(compat_groups[group])),
            "products": ", ".join(compat_groups[group]),
        })

    if unknown and len(unknown) + sum(len(v) for v in compat_groups.values()) > 1:
        findings.append({
            "rule": f"{regime} 7.5.2.2",
            "severity": "warning",
            "message": pick(rules["class1_compat_unknown_group"], lang).replace(
                "{products}", ", ".join(unknown)
            ),
            "products": ", ".join(unknown),
        })
    return findings


def check_adr_mixed_loading(
    entries: list[dict[str, Any]], language: str = "nl", profiles: list[str] | None = None
) -> list[dict[str, str]]:
    """ADR 7.5.2 / 7.5.4 (CV28): mixed loading warnings at class level."""
    rules = get_compliance_rules()["adr_mixed_loading"]
    footnotes = rules["footnotes"]
    lang = _lang(language)
    warnings: list[dict[str, str]] = []

    class1_products: list[tuple[str, str]] = []
    other_class_products: list[tuple[str, str, str]] = []
    # Per compatibility group the packages that fall in it, so the message can
    # say *which* packages it concerns and not merely how many groups there are.
    compat_groups: dict[str, list[str]] = {}
    compat_unknown: list[str] = []
    food_separation: list[str] = []

    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        tokens = _hazard_tokens(product)
        primary = _primary_class(product)
        un = str(product.get("un_number") or "").strip()

        if primary.startswith("1"):
            # 7.5.2.2 is about explosives among themselves, and 1.4S does belong
            # there: the table has an S row and it is not X everywhere — S next
            # to group L is empty, hence forbidden. Footnote (a) to 7.5.2.1 only
            # removes 1.4S from the comparison with *other* classes.
            group = _compat_group(product)
            if group:
                if label not in compat_groups.setdefault(group, []):
                    compat_groups[group].append(label)
            elif label not in compat_unknown:
                compat_unknown.append(label)

        if primary.startswith("1") and not primary.endswith("S"):
            class1_products.append((label, un))
        elif primary and not primary.endswith("S"):
            other_class_products.append((label, un, primary))

        if any(t.startswith("6.1") or t.startswith("6.2") for t in tokens):
            food_separation.append(label)
        elif primary.startswith("9") and un in rules["cv28_class9_un_numbers"]:
            food_separation.append(label)

    if class1_products and other_class_products:
        # Per pair, not per consignment: one forbidden combination does not make
        # the others forbidden, and one permitted combination does not make the
        # rest all right.
        forbidden: list[str] = []
        permitted: dict[str, list[str]] = {}
        for class1_label, class1_un in class1_products:
            for other_label, other_un, other_class in other_class_products:
                note = _mixed_loading_footnote(class1_un, other_un, other_class, footnotes)
                bucket = permitted.setdefault(note, []) if note else forbidden
                for label in (class1_label, other_label):
                    if label not in bucket:
                        bucket.append(label)

        if forbidden:
            warnings.append({
                "rule": "ADR 7.5.2.1",
                "severity": "error",
                "message": pick(rules["rules"]["class1_with_others"], lang),
                "products": ", ".join(forbidden),
            })
        for note in sorted(permitted):
            # Permitted, but not without conditions: footnote (d) moves the
            # placarding and the maximum permitted quantity to class 1.
            warnings.append({
                "rule": f"ADR 7.5.2.1 ({note})",
                "severity": "warning",
                "message": pick(rules["rules"][f"class1_footnote_{note}"], lang),
                "products": ", ".join(permitted[note]),
            })
    warnings.extend(_class1_compatibility(compat_groups, compat_unknown, language, profiles))
    if food_separation:
        # The same provision under a different name: RID puts it in column (18)
        # as CW 28, ADR as CV28. The content of 7.5.4 is word for word the same,
        # so only the citation differs — but an invented code name on a rail
        # document is exactly the kind of inaccuracy the app adds itself.
        _, regime = _compatibility_table(profiles)
        code = "CW28" if regime == "RID" else "CV28"
        warnings.append({
            "rule": f"{regime} {code} / 7.5.4",
            "severity": "warning",
            "message": pick(rules["rules"]["cv28_foodstuffs"], lang),
            "products": ", ".join(food_separation),
        })
    return warnings


def _position_label(entry: dict[str, Any], index: int) -> str:
    return str(entry.get("vehicle") or entry.get("line_id") or f"#{index + 1}")


def check_rid_protective_distance(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, str]]:
    """RID 7.5.3: protective distance in the train.

    This is the provision the railway has no road equivalent for, and that is no
    accident: 7.5.3 is about how a train is assembled, and a road vehicle
    travels alone. Precisely for that reason the ADR chapter could never stand
    in here — it would not give the wrong answer but no answer at all.

    The trigger is the placard, not the division. RID names models 1, 1.5 and
    1.6 and does not name model 1.4, so a wagon carrying only 1.4 goods falls
    outside it.
    """
    rules = get_compliance_rules().get("rid_protective_distance")
    if not rules:
        return []
    lang = _lang(language)
    class1_placards = set(rules["class1_placards"])
    counterpart = set(rules["counterpart_placards"])

    class1_positions: list[str] = []
    counterpart_positions: list[str] = []
    for index, entry in enumerate(entries):
        label = _position_label(entry, index)
        bears_class1 = False
        bears_counterpart = False
        for product in entry.get("products") or []:
            for token in _hazard_tokens(product) + [_primary_class(product)]:
                token = token.strip().upper()
                if token in class1_placards:
                    bears_class1 = True
                elif token in counterpart:
                    bears_counterpart = True
            # Class 1 without a division in the class field: the division is
            # then in the classification code, and without a division there is no
            # telling whether the placard is 1.4 — so the position counts, because
            # not knowing whether a distance is needed must not look like knowing
            # that it is not.
            code = str(product.get("classification_code") or "").strip().upper()
            division = code[:3] if re.match(r"^1\.\d", code) else ""
            if division in class1_placards:
                bears_class1 = True
            elif _primary_class(product) == "1" and not division:
                bears_class1 = True
        if bears_class1 and label not in class1_positions:
            class1_positions.append(label)
        if bears_counterpart and label not in counterpart_positions:
            counterpart_positions.append(label)

    if not class1_positions:
        return []

    pairs = [
        (one, other)
        for one in class1_positions
        for other in counterpart_positions
        if one != other
    ]
    if pairs:
        return [{
            "rule": "RID 7.5.3",
            "severity": "warning",
            "message": pick(rules["rules"]["between_positions"], lang),
            "products": "; ".join(f"{one} ↔ {other}" for one, other in pairs),
        }]
    # No counterpart in this consignment does not mean no distance is needed:
    # the rest of the train is not in CargoPilot.
    return [{
        "rule": "RID 7.5.3",
        "severity": "warning",
        "message": pick(rules["rules"]["train_formation"], lang),
        "products": ", ".join(class1_positions),
    }]


#: The wording of the tunnel result, per outcome. Kept here rather than in the
#: configuration because these are sentences about what the app did, not values
#: read out of the ADR; the figures and the table itself are in the config.
_TUNNEL_MESSAGES: dict[str, dict[str, str]] = {
    "derived": {
        "nl": "De meest restrictieve code van de hele lading is {code} (8.6.3.2). "
              "Doorgang verboden door tunnels van categorie {categories}.",
        "en": "The most restrictive code for the whole load is {code} (8.6.3.2). "
              "Passage forbidden through tunnels of category {categories}.",
        "de": "Der restriktivste Code der gesamten Ladung ist {code} (8.6.3.2). "
              "Durchfahrt durch Tunnel der Kategorie {categories} verboten.",
        "fr": "Le code le plus restrictif de l'ensemble du chargement est {code} "
              "(8.6.3.2). Passage interdit dans les tunnels de catégorie {categories}.",
    },
    "unrestricted": {
        "nl": "De meest restrictieve code van de hele lading is {code} (8.6.3.2): "
              "doorgang toegestaan door alle tunnels.",
        "en": "The most restrictive code for the whole load is {code} (8.6.3.2): "
              "passage permitted through all tunnels.",
        "de": "Der restriktivste Code der gesamten Ladung ist {code} (8.6.3.2): "
              "Durchfahrt durch alle Tunnel erlaubt.",
        "fr": "Le code le plus restrictif de l'ensemble du chargement est {code} "
              "(8.6.3.2) : passage autorisé dans tous les tunnels.",
    },
    "exempt": {
        "nl": "Alle goederen worden overeenkomstig 1.1.3 vervoerd. Die tellen niet "
              "mee bij het vaststellen van de code voor de hele lading en zijn niet "
              "aan tunnelbeperkingen onderworpen (8.6.3.3).",
        "en": "Every item is carried under 1.1.3. Those do not count towards the "
              "code for the whole load and are not subject to tunnel restrictions "
              "(8.6.3.3).",
        "de": "Alle Güter werden nach 1.1.3 befördert. Sie zählen bei der "
              "Bestimmung des Codes für die gesamte Ladung nicht mit und "
              "unterliegen keinen Tunnelbeschränkungen (8.6.3.3).",
        "fr": "Toutes les marchandises sont transportées selon le 1.1.3. Elles ne "
              "comptent pas pour la détermination du code de l'ensemble du "
              "chargement et ne sont pas soumises aux restrictions en tunnel "
              "(8.6.3.3).",
    },
    "lq_marking_only": {
        "nl": "De goederen zelf worden overeenkomstig 1.1.3 vervoerd, maar de "
              "transporteenheid moet de LQ-kenmerking van 3.4.13 dragen. Daarmee "
              "geldt het verbod op doorgang door tunnels van categorie {categories} "
              "(8.6.3.3 en 8.6.4).",
        "en": "The goods themselves are carried under 1.1.3, but the transport unit "
              "has to carry the LQ marking of 3.4.13. That brings the ban on passage "
              "through tunnels of category {categories} with it (8.6.3.3 and 8.6.4).",
        "de": "Die Güter selbst werden nach 1.1.3 befördert, die Beförderungseinheit "
              "muss jedoch die LQ-Kennzeichnung nach 3.4.13 tragen. Damit gilt das "
              "Verbot der Durchfahrt durch Tunnel der Kategorie {categories} "
              "(8.6.3.3 und 8.6.4).",
        "fr": "Les marchandises elles-mêmes relèvent du 1.1.3, mais l'unité de "
              "transport doit porter la marque QL du 3.4.13. L'interdiction de "
              "passage dans les tunnels de catégorie {categories} s'applique donc "
              "(8.6.3.3 et 8.6.4).",
    },
    "incomplete": {
        "nl": "Voor {products} staat geen code voor beperkingen in tunnels in de "
              "regel. Zolang die ontbreekt kan de code voor de hele lading niet "
              "worden vastgesteld (8.6.3.2).",
        "en": "No tunnel restriction code is on the line for {products}. Until it is "
              "there the code for the whole load cannot be determined (8.6.3.2).",
        "de": "Für {products} steht kein Code für Tunnelbeschränkungen in der Zeile. "
              "Solange er fehlt, kann der Code für die gesamte Ladung nicht bestimmt "
              "werden (8.6.3.2).",
        "fr": "Aucun code de restriction en tunnel ne figure sur la ligne pour "
              "{products}. Tant qu'il manque, le code de l'ensemble du chargement ne "
              "peut être déterminé (8.6.3.2).",
    },
    "unknown_code": {
        "nl": "De code {code} bij {products} staat niet in de tabel van 8.6.4. De "
              "code voor de hele lading is daarom niet vastgesteld.",
        "en": "The code {code} on {products} is not in the table of 8.6.4. The code "
              "for the whole load has therefore not been determined.",
        "de": "Der Code {code} bei {products} steht nicht in der Tabelle von 8.6.4. "
              "Der Code für die gesamte Ladung wurde daher nicht bestimmt.",
        "fr": "Le code {code} de {products} ne figure pas au tableau du 8.6.4. Le "
              "code de l'ensemble du chargement n'a donc pas été déterminé.",
    },
}

#: What the answer does *not* cover. The app knows packages, not tanks, and it
#: does not know the route — both of which change the answer, so both are said.
_TUNNEL_NOTE = {
    "nl": "Berekend voor vervoer in colli. Los gestort vervoer of vervoer in tanks "
          "geeft bij de codes B/D, B/E, C/D, C/E en D/E een strengere uitkomst. "
          "Welke tunnels op de route liggen en in welke categorie zij vallen, weet "
          "CargoPilot niet — dat blijft aan de vervoerder (1.9.5).",
    "en": "Computed for carriage in packages. Carriage in bulk or in tanks gives a "
          "stricter answer for the codes B/D, B/E, C/D, C/E and D/E. Which tunnels "
          "lie on the route, and which category they are in, CargoPilot does not "
          "know — that stays with the carrier (1.9.5).",
    "de": "Berechnet für die Beförderung in Versandstücken. Beförderung in loser "
          "Schüttung oder in Tanks ergibt bei den Codes B/D, B/E, C/D, C/E und D/E "
          "ein strengeres Ergebnis. Welche Tunnel auf der Strecke liegen und in "
          "welche Kategorie sie fallen, weiß CargoPilot nicht — das bleibt beim "
          "Beförderer (1.9.5).",
    "fr": "Calculé pour le transport en colis. Le transport en vrac ou en citernes "
          "donne un résultat plus strict pour les codes B/D, B/E, C/D, C/E et D/E. "
          "Quels tunnels se trouvent sur l'itinéraire, et dans quelle catégorie ils "
          "sont classés, CargoPilot l'ignore — cela reste au transporteur (1.9.5).",
}


def _tunnel_code_of(product: dict[str, Any]) -> str:
    """The code from column (15), however it was written into the field.

    It reaches the line as "D/E", as "(D/E)" or — where the ADR says there is no
    restriction — as "-" or "(-)". All three mean the same thing.
    """
    raw = str(product.get("tunnel_code") or "").strip()
    raw = raw.strip("()").strip()
    if raw in {"–", "—"}:
        return "-"
    return raw.upper() if raw else ""


def check_adr_tunnel(
    entries: list[dict[str, Any]],
    language: str = "nl",
    points_status: str | None = None,
    lq_marking_required: bool = False,
) -> dict[str, Any]:
    """ADR 8.6.3: the tunnel restriction code for the whole load.

    Until now the code was printed on the transport document — correctly, per
    5.4.1.1.1 (k) — and evaluated nowhere. That is the more dangerous half of the
    two: a consignor who reads "(D/E)" on a CMR may reasonably assume that
    something has been considered, and nothing had been.

    Two provisions make this more than picking the strictest of a list.

    **8.6.3.2** assigns the most restrictive of the codes present to the *whole
    load*, so a load is not a set of separately restricted substances but one
    unit with one code. The order of restrictiveness is not stated in words; it
    is the order of the table in 8.6.4, and that is where it is read from.

    **8.6.3.3** takes goods carried under 1.1.3 out of the determination
    altogether. They are not subject to tunnel restrictions and must not be
    counted — so for a consignment that stays within the 1.1.3.6 exemption there
    is no code to assign at all, and printing one is not merely unevaluated but
    arguably not applicable. The single exception the article names is the
    transport unit that has to carry the marking of 3.4.13 subject to 3.4.14;
    that unit is restricted for category E tunnels under 8.6.4, whatever its
    goods' own codes say.

    ``points_status`` comes from :func:`check_adr_points` and ``lq_marking_required``
    from :func:`check_lq_eq`, so the two things 8.6.3.3 turns on are read from the
    checks that already establish them rather than derived a second time here.
    """
    rules = get_compliance_rules()["adr_tunnel"]
    lang = _lang(language)
    order: list[str] = rules["order"]
    table: dict[str, Any] = rules["codes"]

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    unknown: list[tuple[str, str]] = []
    present: list[str] = []
    explosive_mass = 0.0

    for entry, index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        label = _product_label(entry, product, index)
        code = _tunnel_code_of(product)
        rows.append({"product": label, "code": code or None})
        if not code:
            missing.append(label)
            continue
        if code not in table:
            unknown.append((label, code))
            continue
        present.append(code)
        if table[code].get("explosive_mass_kg"):
            # The two split codes count the *total* net explosive mass per
            # transport unit, not the mass of the one line that carries them.
            mass = _num(product.get("net_explosive_mass"))
            if mass:
                explosive_mass += mass

    result: dict[str, Any] = {
        "rows": rows,
        "code": None,
        "restricted_categories": [],
        "explosive_mass_kg": round(explosive_mass, 3) if explosive_mass else None,
        "basis": "ADR 8.6.3 / 8.6.4",
        "note": pick(_TUNNEL_NOTE, lang),
    }

    if not rows:
        result["status"] = "not_checked"
        result["message"] = ""
        return result

    # 8.6.3.3 first: what is carried under 1.1.3 does not take part in the
    # determination, and if that is everything there is nothing to determine.
    if points_status == "exempt_possible":
        if lq_marking_required:
            categories = list(rules["lq_marking_categories"])
            result.update({
                "status": "lq_marking_only",
                "restricted_categories": categories,
                "message": pick(_TUNNEL_MESSAGES["lq_marking_only"], lang).format(
                    categories=", ".join(categories)),
            })
        else:
            result["status"] = "exempt"
            result["message"] = pick(_TUNNEL_MESSAGES["exempt"], lang)
        return result

    if unknown:
        label, code = unknown[0]
        result["status"] = "unknown_code"
        result["message"] = pick(_TUNNEL_MESSAGES["unknown_code"], lang).format(
            code=code, products=label)
        return result
    if missing:
        result["status"] = "incomplete"
        result["message"] = pick(_TUNNEL_MESSAGES["incomplete"], lang).format(
            products=", ".join(missing))
        return result

    code = min(present, key=order.index)
    spec = table[code]
    categories = list(spec["packages"])
    threshold = spec.get("explosive_mass_kg")
    if threshold and explosive_mass > threshold:
        categories = list(spec["above"])
    result.update({
        "code": code,
        "restricted_categories": categories,
        "status": "unrestricted" if not categories else "derived",
    })
    result["message"] = pick(
        _TUNNEL_MESSAGES["unrestricted" if not categories else "derived"], lang
    ).format(code=code, categories=", ".join(categories))
    return result


#: The equipment of 8.1.5, in the words a driver checks it by. Kept out of the
#: configuration because these are labels for the user; the *conditions* — which
#: label numbers call for what — are in the configuration, read from the ADR.
_EQUIPMENT_LABELS: dict[str, dict[str, str]] = {
    "wheel_chock": {
        "nl": "Per voertuig een stopblok (wielkeg), passend bij de massa van het "
              "voertuig en de wieldiameter",
        "en": "A wheel chock per vehicle, sized to the vehicle's mass and the wheel "
              "diameter",
        "de": "Je Fahrzeug ein Unterlegkeil, passend zur Fahrzeugmasse und zum "
              "Raddurchmesser",
        "fr": "Une cale de roue par véhicule, adaptée à la masse du véhicule et au "
              "diamètre de la roue",
    },
    "warning_signs": {
        "nl": "Twee zelfstandig staande waarschuwingssignalen",
        "en": "Two self-standing warning signs",
        "de": "Zwei selbststehende Warnzeichen",
        "fr": "Deux signaux d'avertissement autoportants",
    },
    "eye_rinsing_liquid": {
        "nl": "Vloeistof om de ogen te spoelen",
        "en": "Eye-rinsing liquid",
        "de": "Augenspülflüssigkeit",
        "fr": "Liquide de rinçage pour les yeux",
    },
    "warning_vest": {
        "nl": "Per bemanningslid een waarschuwingsvest",
        "en": "A warning vest per crew member",
        "de": "Je Mitglied der Fahrzeugbesatzung eine Warnweste",
        "fr": "Un gilet d'avertissement par membre d'équipage",
    },
    "portable_lighting": {
        "nl": "Per bemanningslid een draagbaar verlichtingsapparaat (8.3.4)",
        "en": "A portable lighting apparatus per crew member (8.3.4)",
        "de": "Je Mitglied der Fahrzeugbesatzung ein tragbares Beleuchtungsgerät (8.3.4)",
        "fr": "Un appareil d'éclairage portatif par membre d'équipage (8.3.4)",
    },
    "gloves": {
        "nl": "Per bemanningslid een paar beschermende handschoenen",
        "en": "A pair of protective gloves per crew member",
        "de": "Je Mitglied der Fahrzeugbesatzung ein Paar Schutzhandschuhe",
        "fr": "Une paire de gants de protection par membre d'équipage",
    },
    "eye_protection": {
        "nl": "Per bemanningslid bescherming voor de ogen (bijv. een veiligheidsbril)",
        "en": "Eye protection per crew member (safety goggles, for instance)",
        "de": "Je Mitglied der Fahrzeugbesatzung Augenschutz (z. B. eine Schutzbrille)",
        "fr": "Une protection des yeux par membre d'équipage (lunettes de sécurité)",
    },
    "escape_mask": {
        "nl": "Per bemanningslid een vluchtmasker voor noodgevallen (gecombineerd "
              "gas/stof filter A1B1E1K1-P1 of A2B2E2K2-P2)",
        "en": "An emergency escape mask per crew member (combined gas/dust filter "
              "A1B1E1K1-P1 or A2B2E2K2-P2)",
        "de": "Je Mitglied der Fahrzeugbesatzung eine Notfall-Fluchtmaske "
              "(Kombinationsfilter A1B1E1K1-P1 oder A2B2E2K2-P2)",
        "fr": "Un masque d'évacuation d'urgence par membre d'équipage (filtre combiné "
              "gaz/poussières A1B1E1K1-P1 ou A2B2E2K2-P2)",
    },
    "shovel": {"nl": "Een schop", "en": "A shovel", "de": "Eine Schaufel",
               "fr": "Une pelle"},
    "drain_seal": {"nl": "Een rioolafdichting", "en": "A drain seal",
                   "de": "Eine Kanalabdeckung", "fr": "Une protection d'obturation "
                                                      "d'égout"},
    "collecting_container": {
        "nl": "Een opvangreservoir", "en": "A collecting container",
        "de": "Ein Auffangbehälter", "fr": "Un récipient collecteur"},
}

_EXTINGUISHER_MESSAGE = {
    "nl": "Per transporteenheid ten minste {count} draagbare brandblusapparaten voor de "
          "brandbaarheidsklassen A, B en C. De totale capaciteit hangt af van de maximaal "
          "toegestane massa van de transporteenheid: {rows} (8.1.4.1). Eén exemplaar van "
          "ten minste 2 kg moet geschikt zijn voor een brand in de motor of de "
          "bestuurderscabine.",
    "en": "At least {count} portable fire extinguishers for flammability classes A, B and "
          "C per transport unit. The total capacity depends on the maximum permissible "
          "mass of the transport unit: {rows} (8.1.4.1). One of at least 2 kg has to be "
          "suitable for a fire in the engine or the driver's cab.",
    "de": "Je Beförderungseinheit mindestens {count} tragbare Feuerlöscher für die "
          "Brandklassen A, B und C. Die Gesamtkapazität hängt von der höchstzulässigen "
          "Masse der Beförderungseinheit ab: {rows} (8.1.4.1). Einer von mindestens 2 kg "
          "muss für einen Brand im Motor oder im Fahrerhaus geeignet sein.",
    "fr": "Au moins {count} extincteurs portatifs pour les classes d'inflammabilité A, B "
          "et C par unité de transport. La capacité totale dépend de la masse maximale "
          "admissible de l'unité de transport : {rows} (8.1.4.1). L'un d'au moins 2 kg "
          "doit convenir à un feu de moteur ou de cabine.",
}

_EXTINGUISHER_EXEMPT_MESSAGE = {
    "nl": "Vervoer overeenkomstig 1.1.3.6: één draagbaar brandblusapparaat voor de "
          "brandbaarheidsklassen A, B en C van ten minste 2 kg poeder (8.1.4.2).",
    "en": "Carriage under 1.1.3.6: one portable fire extinguisher for flammability "
          "classes A, B and C of at least 2 kg of powder (8.1.4.2).",
    "de": "Beförderung nach 1.1.3.6: ein tragbarer Feuerlöscher für die Brandklassen A, "
          "B und C mit mindestens 2 kg Pulver (8.1.4.2).",
    "fr": "Transport selon le 1.1.3.6 : un extincteur portatif pour les classes "
          "d'inflammabilité A, B et C d'au moins 2 kg de poudre (8.1.4.2).",
}

_EQUIPMENT_NOTE = {
    "nl": "Afgeleid uit de gevaarsetiketnummers van de lading, zoals 8.1.5.1 het "
          "voorschrijft. Wat er werkelijk aan boord ligt, weet CargoPilot niet — dit is "
          "de lijst om mee af te vinken, geen vaststelling. De brandblusapparaten hangen "
          "bovendien aan de maximaal toegestane massa van de transporteenheid, en die is "
          "hier niet bekend.",
    "en": "Derived from the hazard label numbers of the load, the way 8.1.5.1 prescribes. "
          "What is actually on board CargoPilot does not know — this is the list to check "
          "against, not a finding. The extinguishers moreover depend on the maximum "
          "permissible mass of the transport unit, which is not known here.",
    "de": "Abgeleitet aus den Gefahrzettelnummern der Ladung, wie 8.1.5.1 es vorschreibt. "
          "Was tatsächlich an Bord ist, weiß CargoPilot nicht — dies ist die Liste zum "
          "Abhaken, keine Feststellung. Die Feuerlöscher hängen zudem von der "
          "höchstzulässigen Masse der Beförderungseinheit ab, die hier nicht bekannt ist.",
    "fr": "Déduit des numéros d'étiquette de danger du chargement, comme le prescrit le "
          "8.1.5.1. Ce qui se trouve réellement à bord, CargoPilot l'ignore : ceci est la "
          "liste à cocher, pas un constat. Les extincteurs dépendent en outre de la masse "
          "maximale admissible de l'unité de transport, inconnue ici.",
}

#: 8.1.5.3 asks for the shovel, the drain seal and the collecting container for
#: *solids and liquids* only. Gases carry the same label numbers 3 and 9 in no
#: case, but class 2 does carry 9-labelled articles, and a gas cylinder needs no
#: shovel. The physical state follows from the classification code: G and A are
#: gases, and class 2 is a gas throughout.
def _label_numbers(product: dict[str, Any]) -> set[str]:
    """The hazard label numbers of a product, as 8.1.5.1 means them.

    Column (5) of Table A, not the class column, because that is what the
    article points at — and the two differ exactly where it matters. Class 2 is
    "2" in the class column and 2.1, 2.2 or 2.3 on the label, and the footnote
    to 8.1.5.2 exempts 2.1, 2.2 and 2.3 from the eye-rinsing liquid while saying
    nothing about a bare "2". Reading the class column would have made a load of
    propane cylinders carry an eye wash the ADR does not ask for.

    The model letter is not part of the number: label 9A is a class 9 label, and
    8.1.5.3 lists "9".
    """
    numbers: set[str] = set()
    raw = str(product.get("labels") or "").strip()
    if raw:
        for token in re.split(r"[,;/\s()+]+", raw):
            match = re.match(r"^(\d(?:\.\d)?)", token.strip().upper())
            if match:
                numbers.add(match.group(1))
    if not numbers:
        # An entry without a labels column — the IMDG-only additions had none —
        # falls back on the division and the subsidiary risks.
        for token in _hazard_tokens(product):
            match = re.match(r"^(\d(?:\.\d)?)", token)
            if match:
                numbers.add(match.group(1))
    return numbers


def _is_gas(product: dict[str, Any]) -> bool:
    return any(number.startswith("2") for number in _label_numbers(product))


def check_adr_equipment(
    entries: list[dict[str, Any]], language: str = "nl",
    points_status: str | None = None,
) -> dict[str, Any]:
    """ADR 8.1.4 and 8.1.5: what has to be aboard the transport unit.

    Equipment was the one heading in ``docs/dg-coverage.md`` that named itself
    "the most common real-world failure" and was absent from every mode. It is
    absent for a reason worth stating: CargoPilot cannot see a vehicle, so it can
    never establish that a wheel chock is in the cab.

    What it *can* do is derive the list, and that turns out to be most of the
    value. 8.1.5.1 says so itself: the equipment is chosen **according to the
    hazard label numbers of the goods loaded**, and it points at the transport
    document to identify them — which is precisely the document this application
    produces. So the label numbers are the input, and the output is the list a
    driver checks against, with the provision beside each line.

    Two things stay outside it. The number of crew members is not known, so the
    per-crew items say "per crew member" rather than a count. And the fire
    extinguishers of 8.1.4.1 hang on the maximum permissible mass of the
    transport unit, which is a property of the vehicle; the three rows of the
    table are given instead of one answer. Where the consignment stays inside the
    1.1.3.6 exemption, 8.1.4.2 replaces the table with a single 2 kg extinguisher
    — which is one of the few places where the exemption makes a visible
    difference to what has to be in the cab.
    """
    rules = get_compliance_rules()["adr_equipment"]
    lang = _lang(language)

    labels: set[str] = set()
    has_non_gas = False
    for _entry, _index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        labels |= _label_numbers(product)
        if not _is_gas(product):
            has_non_gas = True

    if not labels:
        return {"items": [], "status": "not_checked", "labels": [],
                "basis": "ADR 8.1.4 / 8.1.5", "note": pick(_EQUIPMENT_NOTE, lang)}

    items: list[dict[str, str]] = []

    exempt = points_status == "exempt_possible"
    if exempt:
        items.append({"key": "fire_extinguisher", "rule": "ADR 8.1.4.2",
                      "text": pick(_EXTINGUISHER_EXEMPT_MESSAGE, lang)})
    else:
        table = rules["fire_extinguishers"]["rows"]
        rows = "; ".join(
            (f"≤ {row['max_mass_tonnes']} t: {row['total_kg']} kg"
             if row["max_mass_tonnes"] else f"> 7,5 t: {row['total_kg']} kg")
            for row in table
        )
        items.append({
            "key": "fire_extinguisher", "rule": "ADR 8.1.4.1",
            "text": pick(_EXTINGUISHER_MESSAGE, lang).format(
                count=table[0]["count"], rows=rows),
        })

    general = rules["general"]
    for key in general["per_unit"]:
        items.append({"key": key, "rule": "ADR 8.1.5.2",
                      "text": pick(_EQUIPMENT_LABELS[key], lang)})
    for key, excluded in general["per_unit_unless_label"].items():
        # The footnote is an exemption, not a requirement: eye-rinsing liquid is
        # *not* prescribed for the label numbers listed, so a load that carries
        # nothing else does not need it.
        if labels - set(excluded):
            items.append({"key": key, "rule": "ADR 8.1.5.2",
                          "text": pick(_EQUIPMENT_LABELS[key], lang)})
    for key in general["per_crew_member"]:
        items.append({"key": key, "rule": "ADR 8.1.5.2",
                      "text": pick(_EQUIPMENT_LABELS[key], lang)})

    per_label = rules["per_label"]
    if labels & set(per_label["escape_mask"]["labels"]):
        items.append({"key": "escape_mask", "rule": "ADR 8.1.5.3",
                      "text": pick(_EQUIPMENT_LABELS["escape_mask"], lang)})
    spill = per_label["spill_kit"]
    if labels & set(spill["labels"]) and (has_non_gas or not spill["solids_and_liquids_only"]):
        for key in spill["items"]:
            items.append({"key": key, "rule": "ADR 8.1.5.3",
                          "text": pick(_EQUIPMENT_LABELS[key], lang)})

    return {
        "items": items,
        "labels": sorted(labels),
        "status": "derived",
        "basis": "ADR 8.1.4 / 8.1.5",
        "note": pick(_EQUIPMENT_NOTE, lang),
    }


def check_iata_segregation(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, str]]:
    """IATA Table 9.3.A: segregation between packages, lithium rule included."""
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
    """Map a hazard token onto a row of the IMDG segregation table."""
    token = token.strip().upper()
    if not token:
        return None
    if token.startswith("1"):
        # 1.4S falls outside the table for most combinations, but the Code does
        # know 1.4 as a row of its own; the compatibility group is ignored here.
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
    # '2' without a division or '6' without a division cannot be classified
    # reliably; those are skipped rather than guessed at.
    return None


def check_imdg_segregation(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """IMDG 7.2.4: separation between packages based on the class table."""
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
        # IMDG 7.2.3.3: a subsidiary risk of class 1 is treated as division 1.3
        # for segregation purposes.
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
                    # A digit always beats a "*": that one refers on to 7.2.7
                    # and states no distance itself. `not worst` as the test
                    # allowed int("*") as soon as the first cell was a "*" and a
                    # later one a digit — a class 1 package with a subsidiary
                    # risk next to another class 1 package did exactly that.
                    if value in {"1", "2", "3", "4"} and (
                        not worst.isdigit() or int(value) > int(worst)
                    ):
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


def check_imdg_class1_compatibility(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.7.1.4: permitted mixed stowage of compatibility groups."""
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


# Segregation groups that may not travel together (IMDG 7.2.5 read with column
# 16b): the classic dangerous combinations.
_SGG_CONFLICTS: list[tuple[str, str, dict[str, str]]] = [
    ("SGG1", "SGG18", {
        "nl": "zuren en alkaliën",
        "en": "acids and alkalis",
        "de": "Säuren und Laugen", "fr": 'acides et alcalis'}),
    ("SGG1", "SGG6", {
        "nl": "zuren en cyaniden (ontwikkeling van blauwzuur)",
        "en": "acids and cyanides (release of hydrogen cyanide)",
        "de": "Säuren und Cyanide (Freisetzung von Blausäure)", "fr": "acides et cyanures (dégagement d'acide cyanhydrique)"}),
    ("SGG1", "SGG5", {
        "nl": "zuren en chlorieten (ontwikkeling van chloordioxide)",
        "en": "acids and chlorites (release of chlorine dioxide)",
        "de": "Säuren und Chlorite (Freisetzung von Chlordioxid)", "fr": 'acides et chlorites (dégagement de dioxyde de chlore)'}),
    ("SGG1", "SGG8", {
        "nl": "zuren en hypochlorieten (ontwikkeling van chloorgas)",
        "en": "acids and hypochlorites (release of chlorine gas)",
        "de": "Säuren und Hypochlorite (Freisetzung von Chlorgas)", "fr": 'acides et hypochlorites (dégagement de chlore gazeux)'}),
    ("SGG1", "SGG12", {
        "nl": "zuren en nitrieten (ontwikkeling van nitreuze dampen)",
        "en": "acids and nitrites (release of nitrous fumes)",
        "de": "Säuren und Nitrite (Freisetzung nitroser Gase)", "fr": 'acides et nitrites (dégagement de vapeurs nitreuses)'}),
    ("SGG1", "SGG17", {
        "nl": "zuren en aziden (vorming van explosief waterstofazide)",
        "en": "acids and azides (formation of explosive hydrazoic acid)",
        "de": "Säuren und Azide (Bildung von explosiver Stickstoffwasserstoffsäure)", "fr": "acides et azotures (formation d'acide hydrazoïque explosible)"}),
    ("SGG1", "SGG14", {
        "nl": "zuren en permanganaten",
        "en": "acids and permanganates",
        "de": "Säuren und Permanganate", "fr": 'acides et permanganates'}),
    ("SGG1", "SGG15", {
        "nl": "zuren en metaalpoeders (ontwikkeling van waterstof)",
        "en": "acids and powdered metals (release of hydrogen)",
        "de": "Säuren und Metallpulver (Freisetzung von Wasserstoff)", "fr": "acides et métaux en poudre (dégagement d'hydrogène)"}),
    ("SGG16", "SGG1", {
        "nl": "peroxiden en zuren",
        "en": "peroxides and acids",
        "de": "Peroxide und Säuren", "fr": 'peroxydes et acides'}),
]


def check_imdg_segregation_groups(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.5/3.1.4.4: incompatible segregation groups within the consignment."""
    lang = _lang(language)
    products: list[tuple[str, set[str]]] = []
    for entry, index, product in _iter_products(entries):
        groups = set(segregation_groups_for(product.get("un_number", ""),
                                            str(product.get("packing_group") or "")))
        # Manually entered groups count too.
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
                                  "Stoff.", "fr": 'Groupes de séparation {groups} : la colonne 16b de la liste des marchandises dangereuses prescrit ici une séparation. Vérifiez la rubrique de chaque matière.'},
                        lang,
                    ).format(groups=pick(names, lang)),
                    "products": f"{label_a}  ×  {label_b}",
                })
    return warnings


# How strict a segregation provision is, in plain words.
_ACTION_TEXT = {
    # The German IMDG edition distinguishes "entfernt von" (away from) from
    # "getrennt von" (separated from); that difference is the whole point here.
    "away_from": {
        "nl": "uit de buurt van",
        "en": "away from",
        "de": "entfernt von", "fr": "à l'écart de"},
    "separated_from": {
        "nl": "gescheiden van",
        "en": "separated from",
        "de": "getrennt von", "fr": 'séparé de'},
    "separated_by_compartment": {
        "nl": "gescheiden door een volledig compartiment of ruim van",
        "en": "separated by a complete compartment or hold from",
        "de": "durch eine vollständige Abteilung oder einen vollständigen Laderaum getrennt von", "fr": 'séparé par un compartiment ou une cale complète de'},
    "separated_longitudinally": {
        "nl": "in de lengterichting gescheiden door een tussenliggend compartiment of ruim van",
        "en": "separated longitudinally by an intervening complete compartment or hold from",
        "de": "in Längsrichtung durch eine dazwischenliegende vollständige Abteilung oder "
              "einen vollständigen Laderaum getrennt von", "fr": 'séparé longitudinalement par un compartiment ou une cale complète intercalaire de'},
}

# The same four segregation codes as in the table of 7.2.4, so that an SG code
# and a table value can be compared with each other (7.2.3.1).
_ACTION_CODE = {
    "away_from": "1",
    "separated_from": "2",
    "separated_by_compartment": "3",
    "separated_longitudinally": "4",
}


def _classes_of(product: dict[str, Any]) -> set[str]:
    """Primary class, division and subsidiary risks of a package."""
    found: set[str] = set()
    for field in ("class", "subsidiary_risks", "labels"):
        for token in re.split(r"[+,;/\s]+", str(product.get(field) or "")):
            token = token.strip().strip("()")
            if token and re.fullmatch(r"\d(?:\.\d[A-Z]?)?", token):
                found.add(token)
    return found


def _matches_class(target: str, classes: set[str]) -> bool:
    """"class 5.1" touches 5.1; "class 1" touches every division of class 1."""
    if target in classes:
        return True
    if "." not in target:
        return any(c.split(".")[0] == target for c in classes)
    return False


def _wording(code: str, rules: dict[str, Any]) -> str:
    """The description of an SG code, preferably the one belonging to the code.

    Chapter 7.2.8 gives the official wording; the sentence that came from the UN
    card is a paraphrase and remains only as a fallback.
    """
    return imdg_code_text(code) or str(rules.get(code, {}).get("text", ""))


def check_imdg_segregation_provisions(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG column 16b: the segregation provisions (SG) of the substance itself.

    The segregation table of 7.2.4 works on class; column 16b lays provisions per
    substance on top of that. Those codes now come from the Dangerous Goods List
    itself, as it stands in 42-24, and no longer only from the 41-22 UN cards —
    which covered nowhere near every substance. What is checked here is whether
    another consignment in the same shipment is the target of such a provision.
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

    # Provisions that name ordinary cargo — foodstuffs, oils, odour-absorbing
    # cargo. The app does not know what else goes on board, so these are
    # reported as soon as the substance travels, just like the ADR CV28 note.
    raised_cargo: set[tuple[str, str]] = set()
    for source in parties:
        for code in source["codes"]:
            requirement = cargo.get(code)
            if not isinstance(requirement, dict):
                continue
            # SG26 applies only next to certain classes; the rest always.
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

            # Provisions that name a substance explicitly: which UN numbers
            # those are is in dg_compliance.json — checkable and adjustable.
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
                                      "der Wortlaut; bitte prüfen.", "fr": ' Correspondance établie sur le groupe de séparation, plus large que le libellé ; à vérifier.'},
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
                # An exception in the provision ("except 1.4S") excludes that
                # consignment; otherwise the app would warn about something the
                # Code specifically permits.
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
                # "SGG1" says nothing; "SGG1 (acids)" does.
                if hit_class:
                    what = pick(
                        {"nl": "klasse {c}", "en": "class {c}", "de": "Klasse {c}", "fr": 'classe {c}'}, lang
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
                            "de": "Stauen Sie {action} {what}. {wording}", "fr": 'Arrimer {action} {what}. {wording}'},
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
    """IMDG 7.2.3.1: where provisions conflict, column 16b always prevails.

    The class segregation table of 7.2.4 and the substance-specific SG codes of
    column 16b can say different things about the same pair. The Code leaves no
    doubt about that: "In case of conflicting provisions, the provisions of
    column 16b of the Dangerous Goods List, always take precedence."

    Nothing is removed. Both findings stay, with the provision that prevails
    according to the Code alongside them, so it is visible why one sets the other
    aside. Taking away a justified warning is worse than showing one too many;
    that is the same trade-off as with the exemptions of 7.2.6.3.
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
        # Several SG codes can apply to the same pair, in both directions. The
        # strictest determines what has to happen; every code at that level gets
        # named, because they all carry equal weight.
        strictest_code = max(int(f["code"]) for f in column)
        governing = [f for f in column if int(f["code"]) == strictest_code]
        rules = [f["rule"] for f in governing]
        for finding in table:
            if str(finding.get("code")) == str(strictest_code):
                continue  # No conflict: both provisions come out the same.
            finding["superseded_by"] = rules
            finding["severity"] = "info"
            finding["message"] += pick(
                {
                    "nl": " Let op 7.2.3.1: {rules} in kolom 16b gaat hierop voor "
                          "(scheidingscode {code} in plaats van {was}).",
                    "en": " Note 7.2.3.1: {rules} in column 16b takes precedence over this "
                          "(segregation code {code} instead of {was}).",
                    "de": " Beachten Sie 7.2.3.1: {rules} in Spalte 16b geht dem vor "
                          "(Trennkennzahl {code} statt {was}).", "fr": ' Note 7.2.3.1 : {rules} à la colonne 16b prime sur ce résultat (code de séparation {code} au lieu de {was}).'},
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
                          "Klassentrenntabelle vor.", "fr": ' En vertu du 7.2.3.1, cette disposition de la colonne 16b prime sur le tableau de séparation par classe.'},
                lang,
            )
            if strictest_code >= 3:
                finding["severity"] = "error"
    return findings


def check_imdg_segregation_exemptions(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.6.3: substances in the same table need not be segregated.

    This is the exemption that SG72 in column 16b refers to. The app removes no
    warning with it — suppressing a justified message is worse than showing a
    redundant one — but reports the exemption alongside, table and all. That way
    the finding and its legal basis are in view together and the choice stays
    with the consignor.
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
                                  "7.2.6.1.1 bis 7.2.6.1.4 gelten weiterhin.", "fr": ' Note 7.2.6.4 : les réactions dangereuses des 7.2.6.1.1 à 7.2.6.1.4 restent applicables.'},
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
                                  "keine Trennung anzuwenden.{extra}", "fr": "Les deux matières figurent au tableau {name} : aucune séparation n'est à appliquer entre elles.{extra}"},
                        lang,
                    ).format(name=name, extra=extra),
                    "products": f"{label_a}  \u00d7  {label_b}",
                })
    return findings


def append_class8_pair_exception(
    entries: list[dict[str, Any]], findings: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.6.5 next to the pair concerned, not only as general text.

    Two substances of class 8, packing group II or III, which have to stay
    segregated according to column 16b, may nevertheless travel together in
    packages of up to 30 L/30 kg under 7.2.6.5 — provided they do not react
    dangerously with each other and the document carries the declaration of
    5.4.1.5.11.3. That is the same trade-off as with 7.2.6.3: the exemption is
    reported, the warning stays, and the choice stays with the consignor.
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
                          "bleibt bestehen; die Beurteilung liegt beim Versender.", "fr": "Exception possible : les matières de la classe 8 des groupes d'emballage II ou III en colis d'au plus 30 L ou 30 kg n'ont pas à être séparées entre elles, à condition qu'elles ne réagissent pas dangereusement entre elles et que le document de transport porte la mention du 5.4.1.5.11.3. La constatation de séparation ci-dessus reste valable ; l'appréciation appartient au chargeur."},
                lang,
            ),
            "products": "  \u00d7  ".join(pair),
        })
    return findings + extra


def check_imdg_amendment_42_24(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """What Amendment 42-24 changes about the declared substances.

    The substance-specific IMDG layer comes from the 41-22 UN cards, while the
    basic classification comes from ADR 2025. Where 42-24 differs from that, it
    has to appear with the consignment and not only in the documentation.

    The classification is not silently overwritten. If 42-24 changes the class,
    the subsidiary risk or the packing group, then the segregation the app
    computes is based on the old classification, and that is said in so many
    words. Applying an amended class under one's breath would change the outcome
    without anybody being able to see why.
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
                        "de": "Klassifizierung", "fr": 'classification'},
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
                              "42-24.", "fr": "La classification de cette matière a changé dans l'amendement 42-24. L'application calcule la séparation sur la classification du tableau A de l'ADR et ne l'ajuste pas automatiquement ; vérifiez le résultat au regard de la rubrique de la liste des marchandises dangereuses 42-24."},
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


# Divisions that are (almost always) forbidden in aviation; the ICAO TI lists
# chlorine and related 2.3 gases as forbidden on passenger *and* cargo aircraft,
# with only an A1/A2 approval as a way out.
_AIR_FORBIDDEN_DIVISIONS = {"2.3"}


def check_air_forbidden(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """ICAO TI / IATA DGR: divisions that may not travel by air.

    The class column of Table A only says "2" for gases; the division comes from
    the labels. So both the hazard tokens of the product and the division
    resolved via parse_hazards are tested here — otherwise chlorine (UN 1017,
    class "2", label 2.3) stays invisible until /dg/prepare has put the division
    in the class field.
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
                          "(A1/A2).", "fr": "La division 2.3 (gaz toxiques) est interdite au transport aérien, tant sur aéronef de passagers que sur aéronef cargo, à de rares exceptions près. Le transport n'est possible que sous dérogation ou accord préalable des autorités concernées (A1/A2)."},
                lang,
            ),
            "products": _product_label(entry, product, index),
        })
    return warnings


def check_q_value(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """IATA 5.0.2.11: Q value per position for 'all packed in one'.

    Computed with Decimal and without intermediate rounding: two components of
    0.50001 each are 1.00002 together and therefore Q = 1.1 — exceeded. Rounding
    per component first turned that into 1.0, a false negative.

    A component with missing, zero or negative values does not disappear
    silently: the position gets status "incomplete" with the reason alongside.
    """
    rules = get_compliance_rules()["q_value"]
    lang = _lang(language)
    results: list[dict[str, Any]] = []

    for entry in entries:
        products = entry.get("products") or []
        # A position only takes part once somebody has filled in an M (maximum
        # per package according to the packing instruction). The n is filled
        # automatically by /dg/prepare from the net per package; going on that
        # alone put every air consignment on "incomplete", including those where
        # 'all packed in one' does not come into play at all.
        if not any(
            str(product.get("q_max_net_quantity") or "").strip()
            for product in products
        ):
            # Two or more substances in one position without any Q input: then
            # 'all packed in one' *may* apply and nothing has been computed.
            # Skipping that position silently let the consignment count as
            # "checked" as soon as one other position had been filled in — a
            # check that did not run then looked like a check that passed.
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
                                  "Falls All packed in one zutrifft, geben Sie sie an.", "fr": "Aucune valeur Q calculée pour cette position : elle contient plusieurs matières mais n et M n'ont pas été saisis. Si le « tout compris dans un seul emballage » s'applique, indiquez-les."},
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
                # Rounded for display only; the sum uses the raw ratio.
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
                        "de": "Q kann nicht bestimmt werden: ", "fr": 'Q ne peut pas être déterminé : '},
                    lang,
                ) + "; ".join(invalid),
            })
            continue

        if len(components) < 2:
            # One participating product: no 'all packed in one', no Q needed.
            continue

        q_raw = sum((c["_ratio_exact"] for c in components), Decimal(0))
        # Rounded up to one decimal, over the unrounded sum.
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


# Mass in grams, volume in millilitres: the common denominator in which the
# limits of 3.4 (column 7a) and 3.5.1.2 (E codes) are expressed.
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
    "fr": {
        "checked": "Le contrôle Q a été effectué pour les données « all packed in one » saisies.",
        "incomplete": "Le contrôle Q est incomplet : indiquez pour chaque matière participante un n et un M supérieurs à zéro.",
        "exceeded": "La valeur Q calculée est supérieure à 1.",
        "not_checked": "Aucun contrôle Q effectué. Si le « all packed in one » s'applique, indiquez pour chaque matière la quantité nette n et la quantité maximale admissible M.",
    },
}


def q_check_status(q_values: list[dict[str, Any]], language: str = "nl") -> dict[str, str]:
    """Whether the Q check ran, and if not, that this is said.

    A position that was silently skipped was indistinguishable on screen from a
    position that passed. One unchecked position makes the whole consignment
    unchecked: "checked" must not come to mean "one of the two positions was
    checked".
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
    """Every quantity with a unit out of a text, in g or ml.

    '0,5 L' → [(500.0, 'volume')]; '500 ml oder 500 g' → both. A number without
    a unit yields nothing: '0,5' can mean 0.5 g or 0.5 kg, and at an exemption
    limit of all places that must not be guessed at.
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


# A reference to a special provision in column 7a/7b ("siehe SV 340",
# "See SP277"): not a limit the app can test against.
_SPECIAL_PROVISION_REF = re.compile(r"\b(?:siehe|see)\b|\bS[VP]\s*\d+", re.IGNORECASE)

_LQ_MESSAGES = {
    "no_data": {
        "nl": "Geen LQ-waarde (kolom 7a) beschikbaar voor deze stof; niet getoetst.",
        "en": "No LQ value (column 7a) available for this substance; not assessed.",
        "de": "Kein LQ-Wert (Spalte 7a) für diesen Stoff verfügbar; nicht geprüft.", "fr": 'Aucune valeur QL (colonne 7a) disponible pour cette matière ; non évaluée.'},
    "special_provision": {
        "nl": "Kolom 7a verwijst naar een bijzondere bepaling ({raw}); die tekst staat "
              "niet in CargoPilot. Raadpleeg hoofdstuk 3.3.",
        "en": "Column 7a refers to a special provision ({raw}); that text is not held "
              "by CargoPilot. Consult chapter 3.3.",
        "de": "Spalte 7a verweist auf eine Sondervorschrift ({raw}); dieser Text ist "
              "nicht in CargoPilot enthalten. Ziehen Sie Kapitel 3.3 heran.", "fr": 'La colonne 7a renvoie à une disposition spéciale ({raw}) dont CargoPilot ne dispose pas. Consultez le chapitre 3.3.'},
    "not_permitted": {
        "nl": "Kolom 7a is '0': vervoer als gelimiteerde hoeveelheid (3.4) is voor "
              "deze stof niet toegestaan.",
        "en": "Column 7a is '0': carriage as limited quantity (3.4) is not permitted "
              "for this substance.",
        "de": "Spalte 7a ist '0': Die Beförderung als begrenzte Menge (3.4) ist für "
              "diesen Stoff nicht zugelassen.", "fr": "La colonne 7a porte « 0 » : le transport en quantité limitée (3.4) n'est pas autorisé pour cette matière."},
    "missing_inner": {
        "nl": "LQ-grens {limit}: niet getoetst. Vul de netto hoeveelheid per "
              "binnenverpakking in, met eenheid (bijv. '500 g' of '0,5 L').",
        "en": "LQ limit {limit}: not assessed. Enter the net quantity per inner "
              "packaging, with a unit (e.g. '500 g' or '0.5 L').",
        "de": "LQ-Grenze {limit}: nicht geprüft. Geben Sie die Nettomenge je "
              "Innenverpackung mit Einheit an (z. B. '500 g' oder '0,5 L').", "fr": 'Limite QL {limit} : non évaluée. Indiquez la quantité nette par emballage intérieur, avec son unité (p. ex. « 500 g » ou « 0,5 L »).'},
    "unit_mismatch": {
        "nl": "De eenheid van de binnenverpakking ({inner}) past niet bij de "
              "LQ-grens ({limit}): massa en volume zijn niet uitwisselbaar. "
              "Controleer de invoer.",
        "en": "The unit of the inner packaging ({inner}) does not match the LQ limit "
              "({limit}): mass and volume are not interchangeable. Check the input.",
        "de": "Die Einheit der Innenverpackung ({inner}) passt nicht zur LQ-Grenze "
              "({limit}): Masse und Volumen sind nicht austauschbar. Prüfen Sie die "
              "Eingabe.", "fr": "L'unité de l'emballage intérieur ({inner}) ne correspond pas à celle de la limite QL ({limit}) : masse et volume ne sont pas interchangeables. Vérifiez la saisie."},
    "inner_exceeded": {
        "nl": "De netto hoeveelheid per binnenverpakking ({inner}) is groter dan de "
              "LQ-grens van {limit}. Deze regel kan niet als gelimiteerde hoeveelheid "
              "(3.4) reizen en blijft volledig onder de voorschriften vallen.",
        "en": "The net quantity per inner packaging ({inner}) exceeds the LQ limit of "
              "{limit}. This line cannot travel as a limited quantity (3.4) and "
              "remains fully regulated.",
        "de": "Die Nettomenge je Innenverpackung ({inner}) überschreitet die LQ-Grenze "
              "von {limit}. Diese Zeile kann nicht als begrenzte Menge (3.4) befördert "
              "werden und unterliegt weiterhin allen Vorschriften.", "fr": 'La quantité nette par emballage intérieur ({inner}) dépasse la limite QL de {limit}. Cette ligne ne peut pas voyager en quantité limitée (3.4) et reste intégralement soumise à la réglementation.'},
    "missing_gross": {
        "nl": "Binnenverpakking ({inner}) ≤ LQ-grens {limit}. Vul de bruto massa per "
              "collo in om ook de grens van 30 kg (3.4.2) te toetsen.",
        "en": "Inner packaging ({inner}) ≤ LQ limit {limit}. Enter the gross mass per "
              "package to also assess the 30 kg limit (3.4.2).",
        "de": "Innenverpackung ({inner}) ≤ LQ-Grenze {limit}. Geben Sie die Bruttomasse "
              "je Versandstück an, um auch die 30-kg-Grenze (3.4.2) zu prüfen.", "fr": 'Emballage intérieur ({inner}) ≤ limite QL {limit}. Indiquez la masse brute par colis pour évaluer également la limite de 30 kg (3.4.2).'},
    "gross_exceeded": {
        "nl": "Binnenverpakking ({inner}) ≤ LQ-grens {limit}, maar de bruto massa per "
              "collo ({gross} kg) is groter dan de 30 kg van 3.4.2. Deze regel kan zo "
              "niet als gelimiteerde hoeveelheid reizen.",
        "en": "Inner packaging ({inner}) ≤ LQ limit {limit}, but the gross mass per "
              "package ({gross} kg) exceeds the 30 kg of 3.4.2. As packed, this line "
              "cannot travel as a limited quantity.",
        "de": "Innenverpackung ({inner}) ≤ LQ-Grenze {limit}, aber die Bruttomasse je "
              "Versandstück ({gross} kg) überschreitet die 30 kg nach 3.4.2. So "
              "verpackt kann diese Zeile nicht als begrenzte Menge befördert werden.", "fr": 'Emballage intérieur ({inner}) ≤ limite QL {limit}, mais la masse brute par colis ({gross} kg) dépasse les 30 kg du 3.4.2. Emballée ainsi, cette ligne ne peut pas voyager en quantité limitée.'},
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
              "Verpackungsvorschriften von 3.4 gelten weiterhin.", "fr": "Dans les limites du 3.4 : {inner} par emballage intérieur ≤ {limit} et {gross} kg bruts par colis ≤ 30 kg (20 kg pour les plateaux houssés ou filmés, 3.4.3). La marque QL et les prescriptions d'emballage du 3.4 restent applicables."},
}

# Only meaningful next to a points table, so only with a land profile: a line
# that actually travels as LQ does not count towards the 1.1.3.6 points under
# 1.1.3.6.5. The table keeps counting it — an exemption never silently removes
# a result here.
_LQ_POINTS_NOTE = {
    "nl": " Reist deze regel als LQ, dan telt hij volgens 1.1.3.6.5 niet mee in de "
          "1.1.3.6-punten; de puntentabel telt hem volledigheidshalve wél mee.",
    "en": " If this line travels as LQ it does not count towards the 1.1.3.6 points "
          "per 1.1.3.6.5; the points table still includes it for completeness.",
    "de": " Wird diese Zeile als LQ befördert, zählt sie nach 1.1.3.6.5 nicht zu den "
          "Punkten nach 1.1.3.6; die Punktetabelle führt sie der Vollständigkeit "
          "halber dennoch auf.", "fr": " Si cette ligne voyage en quantité limitée, elle ne compte pas dans les points du 1.1.3.6 en vertu du 1.1.3.6.5 ; le tableau des points la reprend néanmoins par souci d'exhaustivité."}

_EQ_MESSAGES = {
    "no_data": {
        "nl": "Geen E-code (kolom 7b) beschikbaar voor deze stof; niet getoetst.",
        "en": "No E code (column 7b) available for this substance; not assessed.",
        "de": "Kein E-Code (Spalte 7b) für diesen Stoff verfügbar; nicht geprüft.", "fr": 'Aucun code E (colonne 7b) disponible pour cette matière ; non évalué.'},
    "special_provision": {
        "nl": "Kolom 7b verwijst naar een bijzondere bepaling ({raw}); die tekst staat "
              "niet in CargoPilot. Raadpleeg hoofdstuk 3.3.",
        "en": "Column 7b refers to a special provision ({raw}); that text is not held "
              "by CargoPilot. Consult chapter 3.3.",
        "de": "Spalte 7b verweist auf eine Sondervorschrift ({raw}); dieser Text ist "
              "nicht in CargoPilot enthalten. Ziehen Sie Kapitel 3.3 heran.", "fr": 'La colonne 7b renvoie à une disposition spéciale ({raw}) dont CargoPilot ne dispose pas. Consultez le chapitre 3.3.'},
    "not_permitted": {
        "nl": "E0: vervoer als vrijgestelde hoeveelheid (3.5) is voor deze stof niet "
              "toegestaan.",
        "en": "E0: carriage as excepted quantity (3.5) is not permitted for this "
              "substance.",
        "de": "E0: Die Beförderung als freigestellte Menge (3.5) ist für diesen Stoff "
              "nicht zugelassen.", "fr": "E0 : le transport en quantité exceptée (3.5) n'est pas autorisé pour cette matière."},
    "missing_inner": {
        "nl": "{code} (max. {inner_cap} g/ml per binnenverpakking, {outer_cap} g/ml "
              "per collo): niet getoetst. Vul de netto hoeveelheid per "
              "binnenverpakking in, met eenheid.",
        "en": "{code} (max. {inner_cap} g/ml per inner packaging, {outer_cap} g/ml per "
              "package): not assessed. Enter the net quantity per inner packaging, "
              "with a unit.",
        "de": "{code} (max. {inner_cap} g/ml je Innenverpackung, {outer_cap} g/ml je "
              "Versandstück): nicht geprüft. Geben Sie die Nettomenge je "
              "Innenverpackung mit Einheit an.", "fr": '{code} (max. {inner_cap} g/ml par emballage intérieur, {outer_cap} g/ml par colis) : non évalué. Indiquez la quantité nette par emballage intérieur, avec son unité.'},
    "missing_outer": {
        "nl": "{code}: binnenverpakking ({inner}) ≤ {inner_cap} g/ml. Vul de netto "
              "hoeveelheid per collo in (met eenheid) om ook de grens van {outer_cap} "
              "g/ml per buitenverpakking te toetsen.",
        "en": "{code}: inner packaging ({inner}) ≤ {inner_cap} g/ml. Enter the net "
              "quantity per package (with a unit) to also assess the {outer_cap} g/ml "
              "limit per outer packaging.",
        "de": "{code}: Innenverpackung ({inner}) ≤ {inner_cap} g/ml. Geben Sie die "
              "Nettomenge je Versandstück (mit Einheit) an, um auch die Grenze von "
              "{outer_cap} g/ml je Außenverpackung zu prüfen.", "fr": '{code} : emballage intérieur ({inner}) ≤ {inner_cap} g/ml. Indiquez la quantité nette par colis (avec son unité) pour évaluer également la limite de {outer_cap} g/ml par emballage extérieur.'},
    "inner_exceeded": {
        "nl": "De netto hoeveelheid per binnenverpakking ({inner}) is groter dan de "
              "{inner_cap} g/ml van {code} (3.5.1.2). Deze regel kan niet als "
              "vrijgestelde hoeveelheid reizen.",
        "en": "The net quantity per inner packaging ({inner}) exceeds the {inner_cap} "
              "g/ml of {code} (3.5.1.2). This line cannot travel as an excepted "
              "quantity.",
        "de": "Die Nettomenge je Innenverpackung ({inner}) überschreitet die "
              "{inner_cap} g/ml von {code} (3.5.1.2). Diese Zeile kann nicht als "
              "freigestellte Menge befördert werden.", "fr": 'La quantité nette par emballage intérieur ({inner}) dépasse les {inner_cap} g/ml du {code} (3.5.1.2). Cette ligne ne peut pas voyager en quantité exceptée.'},
    "outer_exceeded": {
        "nl": "De netto hoeveelheid per collo ({outer}) is groter dan de {outer_cap} "
              "g/ml van {code} (3.5.1.2). Deze regel kan zo niet als vrijgestelde "
              "hoeveelheid reizen.",
        "en": "The net quantity per package ({outer}) exceeds the {outer_cap} g/ml of "
              "{code} (3.5.1.2). As packed, this line cannot travel as an excepted "
              "quantity.",
        "de": "Die Nettomenge je Versandstück ({outer}) überschreitet die {outer_cap} "
              "g/ml von {code} (3.5.1.2). So verpackt kann diese Zeile nicht als "
              "freigestellte Menge befördert werden.", "fr": 'La quantité nette par colis ({outer}) dépasse les {outer_cap} g/ml du {code} (3.5.1.2). Emballée ainsi, cette ligne ne peut pas voyager en quantité exceptée.'},
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
              "Container sind höchstens 1000 Versandstücke zulässig (3.5.5).", "fr": "Dans les limites du {code} : {inner} par emballage intérieur ≤ {inner_cap} g/ml et {outer} par colis ≤ {outer_cap} g/ml (3.5.1.2). Les prescriptions d'emballage et d'épreuve des 3.5.2 et 3.5.3 ainsi que la marque QE restent applicables ; 1 000 colis au plus sont admis par véhicule ou conteneur (3.5.5)."},
    "relief_3_5_1_4": {
        "nl": "Ten hoogste 1 g/ml per binnenverpakking en 100 g/ml per collo: "
              "hiervoor gelden alleen 3.5.2 en 3.5.3 (3.5.1.4). Het EQ-kenmerk van "
              "3.5.4 en de grens van 1000 colli van 3.5.5 gelden niet, en een "
              "tussenverpakking is niet vereist als de binnenverpakkingen met "
              "opvulmateriaal zijn verpakt en er bij vloeistoffen genoeg absorberend "
              "materiaal in de buitenverpakking zit.",
        "en": "At most 1 g/ml per inner packaging and 100 g/ml per package: only "
              "3.5.2 and 3.5.3 apply to these (3.5.1.4). The EQ mark of 3.5.4 and the "
              "1,000-package limit of 3.5.5 do not, and no intermediate packaging is "
              "required where the inner packagings are cushioned and, for liquids, "
              "the outer packaging holds enough absorbent material.",
        "de": "Höchstens 1 g/ml je Innenverpackung und 100 g/ml je Versandstück: "
              "hierfür gelten nur 3.5.2 und 3.5.3 (3.5.1.4). Die EQ-Kennzeichnung "
              "nach 3.5.4 und die Grenze von 1000 Versandstücken nach 3.5.5 gelten "
              "nicht, und eine Zwischenverpackung ist nicht erforderlich, wenn die "
              "Innenverpackungen mit Polstermaterial verpackt sind und bei "
              "Flüssigkeiten genügend saugfähiges Material in der Außenverpackung "
              "vorhanden ist.",
        "fr": "Au plus 1 g/ml par emballage intérieur et 100 g/ml par colis : seuls "
              "les 3.5.2 et 3.5.3 s'y appliquent (3.5.1.4). La marque QE du 3.5.4 et "
              "la limite de 1 000 colis du 3.5.5 ne s'appliquent pas, et aucun "
              "emballage intermédiaire n'est exigé si les emballages intérieurs sont "
              "calés et si, pour les liquides, l'emballage extérieur contient assez "
              "de matériau absorbant.",
    },
}

# ADR 3.4.2 / IMDG 3.4.2.1: total gross mass of an LQ package.
_LQ_GROSS_LIMIT_KG = 30.0
# ADR 3.4.13/3.4.14: above this gross mass of LQ packages the transport unit
# carries the large mark of 3.4.15 — and with it, per 8.6.4, a tunnel
# restriction it would not otherwise have had.
_LQ_MARKING_THRESHOLD_KG = 8000.0
# ADR/IMDG 3.5.5: ten hoogste 1000 EQ-colli per voertuig of container.
_EQ_PACKAGE_CAP = 1000

# ADR 3.5.1.4: the smallest excepted quantities. For the codes E1, E2, E4 and E5
# with at most 1 g or 1 ml per inner packaging and at most 100 g or 100 ml per
# outer packaging, only 3.5.2 (packagings, with the intermediate packaging
# waived where the inner ones are cushioned and, for liquids, absorbed) and
# 3.5.3 (the package tests) apply. Everything else in chapter 3.5 falls away —
# including the marking of 3.5.4 and the cap of 3.5.5, which is what makes this
# more than a note on screen: such packages do not count towards the 1,000.
_EQ_RELIEF_CODES = frozenset({"E1", "E2", "E4", "E5"})
_EQ_RELIEF_INNER = 1.0
_EQ_RELIEF_OUTER = 100.0

#: ADR/IMDG 3.5.1.3, the other provision that only shows up across lines.
_EQ_TOGETHER_MESSAGE = {
    "nl": "Deze positie bevat vrijgestelde hoeveelheden met verschillende E-codes "
          "({codes}). Zijn zij samen in één buitenverpakking verpakt, dan geldt de "
          "meest restrictieve code: ten hoogste {cap} g/ml per buitenverpakking "
          "({code}, 3.5.1.3). De ingevoerde hoeveelheden tellen op tot {total} g/ml.",
    "en": "This position holds excepted quantities with different E codes ({codes}). "
          "Packed together in one outer packaging, the most restrictive code applies: "
          "at most {cap} g/ml per outer packaging ({code}, 3.5.1.3). The entered "
          "quantities total {total} g/ml.",
    "de": "Diese Position enthält freigestellte Mengen mit verschiedenen E-Codes "
          "({codes}). Zusammen in einer Außenverpackung verpackt gilt der "
          "restriktivste Code: höchstens {cap} g/ml je Außenverpackung ({code}, "
          "3.5.1.3). Die eingegebenen Mengen ergeben zusammen {total} g/ml.",
    "fr": "Cette position contient des quantités exceptées avec des codes E "
          "différents ({codes}). Emballées ensemble dans un même emballage "
          "extérieur, le code le plus restrictif s'applique : au plus {cap} g/ml par "
          "emballage extérieur ({code}, 3.5.1.3). Les quantités saisies totalisent "
          "{total} g/ml.",
}


def _fmt_kg(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _assess_lq(
    raw: str, inner: list[tuple[float, str]], gross_kg: float | None, lang: str
) -> dict[str, Any]:
    """Test one line against column 7a and the 30 kg limit of 3.4.2."""
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
    # "500 ml oder 500 g": the variant matching the entered unit is the one that
    # counts.
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
    """Test one line against the E code of column 7b (table 3.5.1.2)."""
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

    # Table 3.5.1.2 counts in grams for solids and in ml for liquids and gases
    # with the same figure; mass and volume therefore share one limit here.
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
    outcome(
        "within_limits", "within_limits",
        code=code,
        inner=_format_base(inner_amount, inner_kind), inner_cap=inner_cap,
        outer=_format_base(outer_amount, outer_kind), outer_cap=outer_cap,
    )
    result["outer_cap"] = outer_cap
    result["outer_amount"] = outer_amount
    # 3.5.1.4: the smallest quantities are subject only to 3.5.2 and 3.5.3.
    if (code in _EQ_RELIEF_CODES and inner_amount <= _EQ_RELIEF_INNER
            and outer_amount <= _EQ_RELIEF_OUTER):
        result["relief_3_5_1_4"] = True
        result["message"] += " " + pick(_EQ_MESSAGES["relief_3_5_1_4"], lang)
    return result


def check_lq_eq(
    entries: list[dict[str, Any]], language: str = "nl", profiles: list[str] | None = None
) -> dict[str, Any]:
    """ADR/IMDG 3.4 and 3.5: test the entered quantities against columns 7a and 7b.

    Until now the LQ value and the E code were shown with their meaning, but
    never compared with what had actually been filled in. This check makes that
    comparison — and nothing more. Qualifying on quantity is not the same as
    being exempt: the mark, the packaging requirements and the tests of 3.4 and
    3.5 stay with the consignor. So a line that falls within the limits is
    reported and never silently taken out of the 1.1.3.6 points calculation,
    exactly as the exemption of IMDG 7.2.6.3 is reported without removing a
    warning.
    """
    lang = _lang(language)
    normalized = sorted({p.upper() for p in (profiles or [])})
    use_imdg = "IMDG" in normalized

    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    statuses: set[str] = set()
    # ADR 3.4.13/3.4.14: above 8 tonnes gross of LQ packages per transport unit,
    # the LQ marking of 3.4.15 on the unit is required. The consignment is read
    # here as one transport unit — the app knows no more than that about the
    # vehicle.
    lq_gross_total_kg = 0.0
    lq_gross_products: list[str] = []

    for entry in entries:
        eq_packages = 0.0
        eq_products: list[str] = []
        # 3.5.1.3, per position: what is packed together in one outer packaging.
        # A position holding several substances is what the application already
        # reads as one outer packaging for the IATA "all packed in one" check;
        # the same reading is used here rather than a second, different one.
        eq_together: list[tuple[str, str, int, float]] = []
        for index, product in enumerate(entry.get("products") or []):
            un = str(product.get("un_number") or "").strip()
            lq_raw = str(product.get("limited_quantity") or "").strip()
            eq_raw = str(product.get("excepted_quantity") or "").strip()
            if not un and not lq_raw and not eq_raw:
                continue
            if product.get("transport_forbidden"):
                # No exemption route for a substance that may not be offered for
                # carriage; the prohibition is already in view.
                continue
            label = _product_label(entry, product, index)

            # The IMDG list (42-24) carries the same columns. Where the product
            # has no value, the list fills it in; where the values differ, that
            # is reported — the check computes with the entered value and does
            # not decide for itself which edition prevails.
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
                                      "Seestrecke gilt.", "fr": "Attention : la liste IMDG (42-24) indique ici {value} ; vérifiez quelle valeur s'applique au trajet maritime."},
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
                # 3.5.1.4 takes the smallest quantities out of the whole of
                # chapter 3.5 except 3.5.2 and 3.5.3, so out of the 3.5.5 cap
                # as well. Counting them would refuse a load the text permits.
                if not eq.get("relief_3_5_1_4"):
                    count = _num(product.get("quantity_packages"))
                    if count:
                        eq_packages += count
                        eq_products.append(label)
                if eq.get("outer_cap"):
                    eq_together.append((label, eq["code"], eq["outer_cap"],
                                        eq.get("outer_amount") or 0.0))

            if lq["status"] == "within_limits" and gross_kg:
                count = _num(product.get("quantity_packages"))
                if count:
                    lq_gross_total_kg += gross_kg * count
                    lq_gross_products.append(label)

        # ADR/IMDG 3.5.1.3: where excepted quantities with different E codes are
        # packed together, the total per outer packaging is capped by the most
        # restrictive of those codes. Each line on its own can be within its own
        # code and the package still be over — which is exactly the case that
        # assessing line by line cannot see.
        codes_together = {code for _label, code, _cap, _amount in eq_together}
        if len(codes_together) > 1:
            strictest = min(eq_together, key=lambda item: item[2])
            together_total = sum(amount for _l, _c, _cap, amount in eq_together)
            if together_total > strictest[2]:
                warnings.append({
                    "rule": "ADR/IMDG 3.5.1.3",
                    "severity": "warning",
                    "message": pick(_EQ_TOGETHER_MESSAGE, lang).format(
                        codes=", ".join(sorted(codes_together)),
                        code=strictest[1],
                        cap=strictest[2],
                        total=_fmt_kg(round(together_total, 3)),
                    ),
                    "products": ", ".join(label for label, _c, _cap, _a in eq_together),
                })
                statuses.add("not_within")

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
                              "zulässig (3.5.5).", "fr": 'Cette position compte {count} colis dans les limites QE ; 1 000 colis de quantités exceptées au plus sont admis par véhicule ou conteneur (3.5.5).'},
                    lang,
                ).format(count=_fmt_kg(eq_packages)),
                "products": ", ".join(eq_products),
            })

    lq_marking_required = (lq_gross_total_kg > _LQ_MARKING_THRESHOLD_KG
                           and bool({"ADR", "RID", "ADN"} & set(normalized)))
    if lq_marking_required:
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
                          "3.4.14 gilt dann nicht mehr.", "fr": "Les colis situés dans les limites QL totalisent {tonnes} kg bruts. Au-delà de 8 tonnes par unité de transport, la marque QL du 3.4.15 (250 × 250 mm) est exigée à l'avant et à l'arrière (3.4.13) ; la dispense du 3.4.14 ne s'applique plus."},
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
        # Read by the tunnel check: 8.6.3.3 leaves 1.1.3 goods out of the
        # determination *except* where this marking is required.
        "lq_marking_required": lq_marking_required,
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
                      "nicht verändert.", "fr": "Rester dans les limites n'équivaut pas à être exempté : la marque QL ou QE et les prescriptions d'emballage des 3.4 et 3.5 demeurent des conditions. Le calcul des points du 1.1.3.6 n'est pas modifié par ce résultat."},
            lang,
        ),
    }


def check_compliance(
    entries: list[dict[str, Any]],
    profiles: list[str],
    language: str = "nl",
) -> dict[str, Any]:
    """Run every relevant check for the chosen regulatory profiles."""
    rules = get_compliance_rules()
    result: dict[str, Any] = {
        "sources": rules["sources"],
        "profiles": profiles,
        # Which regulatory editions this result used. The tables of chapter 7.2
        # are unchanged under 42-24; the substance-specific layer comes from
        # 41-22 with the 42-24 differences laid over it. What that layer does not
        # cover is in IMDG_42_24_not_covered.
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

    # What this result was computed with, in one id — usable in a report and in
    # the compliance annex to an export.
    result["regulatory_manifest"] = summary()

    # A rule set that has expired and has not been replaced is not a detail:
    # this check is then computing with text that no longer applies. The result
    # stands, but says for itself that it rests on expired rules.
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
                          "ziehen Sie die geltende Ausgabe heran.", "fr": "{edition} a expiré le {on}. Cette vérification calcule avec une édition qui n'est plus en vigueur ; mettez CargoPilot à jour ou consultez l'édition applicable."},
                language,
            ).format(edition=stale["edition"], on=stale["expired_on"]),
            "products": ", ".join(stale["profiles"]),
        })

    if {"ADR", "RID", "ADN"} & normalized:
        land = sorted({"ADR", "RID", "ADN"} & normalized)
        result["adr_points"] = check_adr_points(entries, language, land)
        result["adr_mixed_loading"] = check_adr_mixed_loading(entries, language, land)
        if "RID" in normalized:
            # 7.5.3 has no road equivalent and therefore does not belong with
            # the borrowed tables, but it does belong in the same list: that one
            # reaches both the panel and the export, and a rail provision that
            # only appears on screen is not on the document.
            result["adr_mixed_loading"] += check_rid_protective_distance(entries, language)
        # ADN answers the exemption question with its own rule, so it gets its
        # own result rather than borrowing the points total.
        if "ADN" in normalized:
            result["adn_exemption"] = check_adn_exemption(entries, language)
        note = basis_note(land, "7.5.2", language)
        if note:
            result["adr_mixed_loading_basis_note"] = note

    # LQ/EQ applies to the land modes *and* to sea transport; air has its own
    # system in the Y packing instructions, which is not claimed here.
    if {"ADR", "RID", "ADN", "IMDG"} & normalized:
        result["lq_eq"] = check_lq_eq(entries, language, sorted(normalized))

    # The tunnel code is a road provision and only a road one: RID table A has
    # no column (15) and the ADN document does not carry the code either. It
    # runs after the two checks it depends on, because 8.6.3.3 turns on whether
    # the goods travel under 1.1.3 and whether the unit needs the 3.4.13 mark.
    if "ADR" in normalized:
        # 8.1.5.1 chooses the equipment by the hazard label numbers of the goods
        # loaded, and 8.1.4.2 by whether the load stays inside 1.1.3.6.
        result["adr_equipment"] = check_adr_equipment(
            entries, language,
            points_status=(result.get("adr_points") or {}).get("status"))
        result["adr_tunnel"] = check_adr_tunnel(
            entries,
            language,
            points_status=(result.get("adr_points") or {}).get("status"),
            lq_marking_required=bool(
                (result.get("lq_eq") or {}).get("lq_marking_required")),
        )

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
        # Whether the Q check actually ran belongs with the result and not with
        # one endpoint. Until v1.32.0 this was computed in the route, so the
        # panel reported "no Q check performed" while the export said nothing
        # about it — precisely the place where the document leaves the building.
        # The export check in exporter.py writes for itself that the screen must
        # never be the only place where this is enforced.
        result["q_check_status"] = q_check_status(result["q_values"], language)
        cao = [
            _product_label(entry, product, index)
            for entry, index, product in _iter_products(entries)
            if str(product.get("cargo_aircraft_only") or "").strip().upper() in {"Y", "YES", "JA", "TRUE", "1"}
        ]
        result["cargo_aircraft_only_products"] = cao

    return result
