"""Nalevingscontroles voor gevaarlijke stoffen: ADR 1.1.3.6-punten, ADR 7.5.2
samenlading en IATA Table 9.3.A-segregatie plus Q-waarde (5.0.2.11).

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
from app.services.dg import amendment_42_24
from app.services.dg.enrichment import (
    card_data_for,
    segregation_group_label,
    segregation_groups_for,
    segregation_provisions,
)


@lru_cache
def get_compliance_rules() -> dict[str, Any]:
    path = get_settings().config_dir / "dg_compliance.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _lang(language: str) -> str:
    return "en" if str(language).lower().startswith("en") else "nl"


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
                "message": codes[worst][lang],
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
                    "message": rules["note"][lang],
                    "products": f"{label_a}  ×  {label_b}",
                })
            elif note and group_a != group_b:
                seen.add(pair_id)
                warnings.append({
                    "rule": f"IMDG 7.2.7.1.4 ({group_a} × {group_b})",
                    "severity": "warning",
                    "message": note[lang],
                    "products": f"{label_a}  ×  {label_b}",
                })
    return warnings


# Scheidingsgroepen die onderling niet samen mogen (IMDG 7.2.5 in samenhang met
# kolom 16b): de klassieke gevaarlijke combinaties.
_SGG_CONFLICTS: list[tuple[str, str, str, str]] = [
    ("SGG1", "SGG18", "zuren en alkaliën", "acids and alkalis"),
    ("SGG1", "SGG6", "zuren en cyaniden (ontwikkeling van blauwzuur)",
     "acids and cyanides (release of hydrogen cyanide)"),
    ("SGG1", "SGG5", "zuren en chlorieten (ontwikkeling van chloordioxide)",
     "acids and chlorites (release of chlorine dioxide)"),
    ("SGG1", "SGG8", "zuren en hypochlorieten (ontwikkeling van chloorgas)",
     "acids and hypochlorites (release of chlorine gas)"),
    ("SGG1", "SGG12", "zuren en nitrieten (ontwikkeling van nitreuze dampen)",
     "acids and nitrites (release of nitrous fumes)"),
    ("SGG1", "SGG17", "zuren en aziden (vorming van explosief waterstofazide)",
     "acids and azides (formation of explosive hydrazoic acid)"),
    ("SGG1", "SGG14", "zuren en permanganaten", "acids and permanganates"),
    ("SGG1", "SGG15", "zuren en metaalpoeders (ontwikkeling van waterstof)",
     "acids and powdered metals (release of hydrogen)"),
    ("SGG16", "SGG1", "peroxiden en zuren", "peroxides and acids"),
]


def check_imdg_segregation_groups(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.5/3.1.4.4: onverenigbare scheidingsgroepen binnen de zending."""
    lang = _lang(language)
    products: list[tuple[str, set[str]]] = []
    for entry, index, product in _iter_products(entries):
        groups = set(segregation_groups_for(product.get("un_number", "")))
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
            for code_a, code_b, nl, en in _SGG_CONFLICTS:
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
                    "message": (
                        f"Scheidingsgroepen {nl}: kolom 16b van de Dangerous Goods List "
                        "schrijft hier scheiding voor. Controleer de vermelding per stof."
                        if lang == "nl"
                        else f"Segregation groups {en}: column 16b of the Dangerous Goods "
                        "List prescribes segregation here. Check the entry per substance."
                    ),
                    "products": f"{label_a}  ×  {label_b}",
                })
    return warnings


# Hoe streng een scheidingsvoorschrift is, in gewone taal.
_ACTION_TEXT = {
    "away_from": ("uit de buurt van", "away from"),
    "separated_from": ("gescheiden van", "separated from"),
    "separated_by_compartment": (
        "gescheiden door een volledig compartiment of ruim van",
        "separated by a complete compartment or hold from",
    ),
    "separated_longitudinally": (
        "in de lengterichting gescheiden door een tussenliggend compartiment of ruim van",
        "separated longitudinally by an intervening complete compartment or hold from",
    ),
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


def check_imdg_segregation_provisions(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG kolom 16b: de scheidingsvoorschriften (SG) van de stof zelf.

    De scheidingstabel van 7.2.4 werkt op klasse; kolom 16b legt daarbovenop
    voorschriften per stof. Die codes staan sinds de UN-kaarten per UN-nummer
    vast, met de tekst die erbij hoort. Hier wordt gekeken of een andere partij
    in dezelfde zending het doel van zo'n voorschrift is.
    """
    lang = _lang(language)
    rules = segregation_provisions()

    parties: list[dict[str, Any]] = []
    for entry, index, product in _iter_products(entries):
        un = str(product.get("un_number") or "").strip()
        card = card_data_for(un)
        groups = set(segregation_groups_for(un))
        for token in re.split(r"[,;/\s]+", str(product.get("segregation_group") or "")):
            if token.strip().upper().startswith("SGG"):
                groups.add(token.strip().upper())
        parties.append({
            "label": _product_label(entry, product, index),
            "un": "".join(ch for ch in un if ch.isdigit()).zfill(4) if un else "",
            "codes": list(card.get("segregation_codes") or []),
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
                "message": f"{requirement[lang]} {rules.get(code, {}).get('text', '')}".strip(),
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
                        caveat = (
                            " Gematcht op de scheidingsgroep, die ruimer is dan de tekst; controleer."
                            if lang == "nl"
                            else " Matched on the segregation group, which is broader than the "
                            "wording; verify."
                        )
                    warnings.append({
                        "rule": f"IMDG 16b ({code})",
                        "severity": "warning",
                        "message": f"{rule['text']}{caveat}",
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
                action_nl, action_en = _ACTION_TEXT.get(
                    str(rule.get("action")), ("gescheiden van", "separated from")
                )
                # "SGG1" zegt niets; "SGG1 (zuren)" wel.
                if hit_class:
                    what = f"klasse {hit_class}"
                    what_en = f"class {hit_class}"
                else:
                    what = f"{hit_group} ({segregation_group_label(hit_group, 'nl')})"
                    what_en = f"{hit_group} ({segregation_group_label(hit_group, 'en')})"
                warnings.append({
                    "rule": f"IMDG 16b ({code})",
                    "severity": "warning",
                    "message": (
                        f"Stuw {action_nl} {what}. {rule['text']}"
                        if lang == "nl"
                        else f"Stow {action_en} {what_en}. {rule['text']}"
                    ),
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
            finding["message"] += (
                f" Let op 7.2.3.1: {', '.join(rules)} in kolom 16b gaat hierop voor "
                f"(scheidingscode {strictest_code} in plaats van {finding['code']})."
                if lang == "nl"
                else f" Note 7.2.3.1: {', '.join(rules)} in column 16b takes precedence "
                f"over this (segregation code {strictest_code} instead of {finding['code']})."
            )
        for finding in governing:
            finding["takes_precedence_over"] = [f["rule"] for f in table]
            finding["message"] += (
                " Deze bepaling uit kolom 16b gaat volgens 7.2.3.1 voor op de "
                "klassescheidingstabel."
                if lang == "nl"
                else " Per 7.2.3.1 this column 16b provision takes precedence over the "
                "class segregation table."
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
                    extra = (
                        " Let op 7.2.6.4: de gevaarlijke reacties van 7.2.6.1.1 t/m "
                        "7.2.6.1.4 blijven gelden."
                        if lang == "nl"
                        else " Note 7.2.6.4: the dangerous reactions of 7.2.6.1.1 to "
                        "7.2.6.1.4 continue to apply."
                    )
                findings.append({
                    "rule": f"IMDG {name}",
                    "severity": "info",
                    "message": (
                        f"Beide stoffen staan in tabel {name}: hiertussen hoeft geen "
                        f"scheiding te worden toegepast.{extra}"
                        if lang == "nl"
                        else f"Both substances appear in table {name}: no segregation needs "
                        f"to be applied between them.{extra}"
                    ),
                    "products": f"{label_a}  \u00d7  {label_b}",
                })
    return findings


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
                "rule": f"IMDG {amendment_42_24.amendment()} — classificatie"
                        if lang == "nl"
                        else f"IMDG {amendment_42_24.amendment()} — classification",
                "severity": "warning",
                "message": (
                    "De classificatie van deze stof is in 42-24 gewijzigd. De app rekent de "
                    "scheiding door op de classificatie van ADR Tabel A en past die niet "
                    "vanzelf aan; controleer de uitkomst tegen de vermelding in de "
                    "Dangerous Goods List van 42-24."
                    if lang == "nl"
                    else "The classification of this substance changed in 42-24. The app "
                    "computes segregation on the ADR Table A classification and does not "
                    "adjust it automatically; check the outcome against the 42-24 Dangerous "
                    "Goods List entry."
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
                "note": (
                    "Q kan niet worden bepaald: " + "; ".join(invalid)
                    if lang == "nl"
                    else "Q cannot be determined: " + "; ".join(invalid)
                ),
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
            "IMDG_per_substance": (
                "Amendment 41-22 (Cantell UN-kaarten, 2023) met de verschillenlaag 42-24"
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

    if {"ADR", "RID", "ADN"} & normalized:
        result["adr_points"] = check_adr_points(entries, language)
        result["adr_mixed_loading"] = check_adr_mixed_loading(entries, language)

    if "IMDG" in normalized:
        result["imdg_segregation"] = apply_column_16b_precedence(
            check_imdg_segregation(entries, language)
            + check_imdg_class1_compatibility(entries, language)
            + check_imdg_segregation_groups(entries, language)
            + check_imdg_segregation_provisions(entries, language)
            + check_imdg_segregation_exemptions(entries, language),
            language,
        ) + check_imdg_amendment_42_24(entries, language)
        result["imdg_note"] = rules["imdg_segregation"]["note"][_lang(language)]
        groups = rules.get("imdg_segregation_groups")
        if groups:
            lang = _lang(language)
            result["imdg_segregation_groups"] = {
                "note": groups["note"][lang],
                "class8_exception": groups["class8_exception"][lang],
                "groups": [
                    {"code": item["code"], "label": item[lang]} for item in groups["groups"]
                ],
            }

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
