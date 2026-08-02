"""Verrijking van UN-vermeldingen voor automatische invulling per modaliteit.

Feitencompilatie als invulhulp; de actuele uitgave van ADR/RID/ADN, de IMDG-code
en de IATA DGR blijft altijd leidend. Bronnen:
- EmS per UN-nummer: de index van IMO MSC.1/Circ.1588/Rev.3 (EmS Guide), met
  alle brandschema's F-A t/m F-J en lekkageschema's S-A t/m S-Z. Zie
  seed/dg/ems.json. Voor de enkele UN-nummers die daar niet in staan geldt een
  indicatieve klassestandaard, die als zodanig wordt gemarkeerd.
- Vrijgestelde hoeveelheden (E-codes): ADR/IMDG/IATA 3.5.1.2.
- Luchtvrachtregels: IATA Guidance Document for Lithium Batteries and Sodium ion
  Batteries (2026) en de IATA DGR; ICAO TI voor het verbod op klasse 2.3.
- Milieugevaarlijk/marine pollutant: UN 3077/3082 en ADR-classificatiecodes
  M6/M7 (IMDG 2.10).
- Vervoersverbod: de etikettenkolom van ADR Tabel A.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from app.services.dg import amendment_42_24

# EmS (brand, lekkage) per UN-nummer — geladen uit backend/seed/dg/ems.json.
_SEED_EMS = Path(__file__).resolve().parents[3] / "seed" / "dg" / "ems.json"
_ems_lock = threading.Lock()
_ems_cache: dict[str, Any] | None = None


def _load_ems() -> dict[str, Any]:
    global _ems_cache
    with _ems_lock:
        if _ems_cache is None:
            _ems_cache = json.loads(_SEED_EMS.read_text(encoding="utf-8"))
    return _ems_cache


def lookup_ems(un_number: str, packing_group: str = "") -> dict[str, Any] | None:
    """EmS-vermelding voor een UN-nummer uit de EmS Guide-index.

    Enkele vermeldingen hebben per verpakkingsgroep een eigen schema (bijv.
    UN 1826 en UN 2031) of kennen varianten met een eigen omschrijving
    (UN 3166, gas- of vloeistofaangedreven voertuigen). Die worden hier
    meegegeven zodat de interface de keuze kan tonen.
    """
    digits = "".join(ch for ch in str(un_number or "") if ch.isdigit()).zfill(4)
    entry = _load_ems()["entries"].get(digits)
    if not entry:
        # UN-nummers die Amendment 42-24 toevoegt staan nog niet in de EmS Guide-
        # index van 2022; hun schema's komen uit de 42-24-bron.
        entry = amendment_42_24.ems_additions().get(digits)
    if not entry:
        return None

    if "by_packing_group" in entry:
        groups = entry["by_packing_group"]
        pg = str(packing_group or "").strip().upper()
        # Exacte treffer, anders de variant zonder */† -markering.
        chosen = groups.get(pg) or next(
            (v for k, v in sorted(groups.items()) if k.rstrip("*†") == pg), None
        )
        if chosen:
            return {**chosen, "packing_group": pg, "packing_group_options": groups}
        return {"packing_group_options": groups}

    if "variants" in entry:
        return {"variants": entry["variants"]}

    return entry


# Wat "yes/no/maybe" in kolom 4 van de Dangerous Goods List betekent, in gewone taal.
_MARINE_POLLUTANT_TEXT = {
    True: {
        "yes": "Marine pollutant: ja — merken en vermelden op het vervoersdocument.",
        "no": "Marine pollutant: nee.",
        "maybe": "Marine pollutant: hangt van de stof af. Beoordeel aan de criteria van "
                 "IMDG 2.10 en merk zo nodig alsnog.",
    },
    False: {
        "yes": "Marine pollutant: yes — mark and declare on the transport document.",
        "no": "Marine pollutant: no.",
        "maybe": "Marine pollutant: depends on the substance. Assess against the criteria "
                 "of IMDG 2.10 and mark if it meets them.",
    },
}

# Scheidingsgroepen (IMDG 3.1.4.4) — geladen uit seed/dg/segregation_groups.json.
_SEED_SGG = Path(__file__).resolve().parents[3] / "seed" / "dg" / "segregation_groups.json"
_sgg_cache: dict[str, Any] | None = None


def _load_sgg() -> dict[str, Any]:
    global _sgg_cache
    with _ems_lock:
        if _sgg_cache is None:
            _sgg_cache = json.loads(_SEED_SGG.read_text(encoding="utf-8"))
    return _sgg_cache


def segregation_groups_for(un_number: str) -> list[str]:
    """Scheidingsgroepcodes van een UN-nummer, bijv. ['SGG1', 'SGG18']."""
    digits = "".join(ch for ch in str(un_number or "") if ch.isdigit()).zfill(4)
    return list(_load_sgg()["by_un"].get(digits, []))


# Stof-specifieke IMDG-gegevens uit de UN-kaarten (un_cards/), samengevat door
# scripts/extract_un_card_data.py: marine pollutant (kolom 4), stuwagecodes SW
# (16a), scheidingscodes SG (16b) en bulkvervoer. De scheidingsgroepen hierboven
# zeggen tot welke groep een stof hoort; deze codes zeggen wat dat betekent.
_SEED_CARDS = Path(__file__).resolve().parents[3] / "seed" / "dg" / "card_data.json"
_cards_cache: dict[str, Any] | None = None
_provisions_cache: dict[str, Any] | None = None


def _load_card_data() -> dict[str, Any]:
    global _cards_cache
    with _ems_lock:
        if _cards_cache is None:
            try:
                _cards_cache = json.loads(_SEED_CARDS.read_text(encoding="utf-8"))["entries"]
            except (OSError, ValueError, KeyError):  # pragma: no cover - seed ontbreekt
                _cards_cache = {}
    return _cards_cache


def segregation_provisions() -> dict[str, Any]:
    """De SG-voorschriften met hun betekenis, zoals op de kaarten geformuleerd."""
    global _provisions_cache
    with _ems_lock:
        if _provisions_cache is None:
            try:
                raw = json.loads(_SEED_CARDS.read_text(encoding="utf-8"))
                _provisions_cache = raw.get("segregation_provisions", {})
            except (OSError, ValueError):  # pragma: no cover - seed ontbreekt
                _provisions_cache = {}
    return _provisions_cache


# De betekenis van de codes uit kolom 16a en 16b, gelezen uit hoofdstuk 7.1.5,
# 7.1.6 en 7.2.8 van de IMDG-code zelf. De kaarten zeggen wélke codes een stof
# draagt; deze tabel zegt wat ze betekenen — voorheen alleen als brokstuk
# beschikbaar uit de kaarttekst.
_SEED_CODES = Path(__file__).resolve().parents[3] / "seed" / "dg" / "imdg_codes.json"
_codes_cache: dict[str, Any] | None = None


def _load_imdg_codes() -> dict[str, Any]:
    global _codes_cache
    with _ems_lock:
        if _codes_cache is None:
            try:
                _codes_cache = json.loads(_SEED_CODES.read_text(encoding="utf-8"))
            except (OSError, ValueError):  # pragma: no cover - seed ontbreekt
                _codes_cache = {}
    return _codes_cache


def imdg_code_text(code: str) -> str:
    """Omschrijving van een SW-, H- of SG-code, of leeg als die onbekend is.

    Een gereserveerde code levert bewust niets op: "[Reserved]" is geen
    voorschrift en hoort niet als begeleiding op het scherm.
    """
    key = str(code or "").strip().upper()
    for section in ("stowage_codes", "handling_codes", "segregation_codes"):
        entry = _load_imdg_codes().get(section) or {}
        text = (entry.get("codes") or {}).get(key)
        if text:
            return text
    return ""


def describe_imdg_codes(codes: list[str]) -> list[dict[str, str]]:
    """Codes met hun omschrijving, in de volgorde waarin ze gegeven zijn."""
    described = []
    for code in codes:
        text = imdg_code_text(code)
        if text:
            described.append({"code": str(code).strip().upper(), "text": text})
    return described


def card_data_for(un_number: str) -> dict[str, Any]:
    """IMDG-gegevens van de UN-kaart, of een leeg dict als die er niet is."""
    digits = "".join(ch for ch in str(un_number or "") if ch.isdigit()).zfill(4)
    entry = _load_card_data().get(digits)
    return dict(entry) if isinstance(entry, dict) else {}


def segregation_group_label(code: str, language: str = "nl") -> str:
    for group in _load_sgg()["groups"]:
        if group["code"] == code:
            return group.get(language) or group.get("nl") or group["en"]
    return code


def ems_schedule_label(code: str, language: str = "nl") -> str:
    """Omschrijving van een brand- of lekkageschema, bijv. 'F-E' → '…'."""
    data = _load_ems()
    key = "fire_schedules" if str(code).upper().startswith("F") else "spillage_schedules"
    item = data.get(key, {}).get(str(code).strip().upper())
    if not item:
        return ""
    return item.get(language) or item.get("nl") or ""


def describe_ems(ems_code: str, language: str = "nl") -> str:
    """'F-E, S-E' → 'F-E (…) · S-E (…)' voor weergave in de interface."""
    parts = []
    for code in re.split(r"[,;/]\s*", str(ems_code or "")):
        code = code.strip().upper()
        label = ems_schedule_label(code, language)
        parts.append(f"{code} ({label})" if label else code)
    return " · ".join(p for p in parts if p)


# Indicatieve EmS-standaard per klasse (IMDG DGL volgt in de meeste gevallen
# deze patronen; afwijkingen per stof komen voor — daarom "indicatief").
EMS_DEFAULT_BY_CLASS: dict[str, tuple[str, str]] = {
    "1": ("F-B", "S-X"),
    "2.1": ("F-D", "S-U"),
    "2.2": ("F-C", "S-V"),
    "2.3": ("F-C", "S-U"),
    "3": ("F-E", "S-D"),
    "4.1": ("F-A", "S-G"),
    "4.2": ("F-A", "S-J"),
    "4.3": ("F-G", "S-N"),
    "5.1": ("F-A", "S-Q"),
    "5.2": ("F-J", "S-R"),
    "6.1": ("F-A", "S-A"),
    "6.2": ("F-A", "S-T"),
    "7": ("F-I", "S-S"),
    "8": ("F-A", "S-B"),
    "9": ("F-A", "S-F"),
}

# Vrijgestelde hoeveelheden (ADR/IMDG/IATA 3.5.1.2):
# code -> (max netto per binnenverpakking, max netto per buitenverpakking), in g of ml.
EXCEPTED_QUANTITY_LIMITS: dict[str, tuple[int, int]] = {
    "E1": (30, 1000),
    "E2": (30, 500),
    "E3": (30, 300),
    "E4": (1, 500),
    "E5": (1, 300),
}

# Luchtvrachtregels per UN-nummer. Bron: IATA Guidance Document for Lithium
# Batteries and Sodium ion Batteries (editie 2026) en de IATA DGR.
AIR_RULES_BY_UN: dict[str, dict[str, Any]] = {
    "3480": {
        "cargo_aircraft_only": True,
        "iata_packing_instruction": "965",
        "note_nl": "Lithium-ionbatterijen (los verpakt): verboden als vracht op passagiersvliegtuigen, dus uitsluitend Cargo Aircraft Only met CAO-label. IATA PI 965, laadtoestand ten hoogste 30% van de nominale capaciteit; hoger uitsluitend met goedkeuring van het land van herkomst en van de exploitant (bijzondere bepaling A331).",
        "note_en": "Lithium-ion batteries (packed by themselves): forbidden as cargo on passenger aircraft, so Cargo Aircraft Only with CAO label. IATA PI 965, state of charge no more than 30% of rated capacity; higher only with approval of the State of Origin and the State of the Operator (special provision A331).",
    },
    "3090": {
        "cargo_aircraft_only": True,
        "iata_packing_instruction": "968",
        "note_nl": "Lithium-metaalbatterijen (los verpakt): verboden als vracht op passagiersvliegtuigen, uitsluitend Cargo Aircraft Only met CAO-label. IATA PI 968; vervoer op een passagiersvliegtuig alleen onder goedkeuring volgens bijzondere bepaling A201.",
        "note_en": "Lithium metal batteries (packed by themselves): forbidden as cargo on passenger aircraft, Cargo Aircraft Only with CAO label. IATA PI 968; carriage on a passenger aircraft only under an approval per special provision A201.",
    },
    "3481": {
        "iata_packing_instruction": "966/967",
        "note_nl": "Lithium-ionbatterijen met of in apparatuur: IATA PI 966 (met apparatuur) of PI 967 (in apparatuur).",
        "note_en": "Lithium-ion batteries packed with or contained in equipment: IATA PI 966 (packed with) or PI 967 (contained in).",
    },
    "3091": {
        "iata_packing_instruction": "969/970",
        "note_nl": "Lithium-metaalbatterijen met of in apparatuur: IATA PI 969 (met apparatuur) of PI 970 (in apparatuur).",
        "note_en": "Lithium metal batteries packed with or contained in equipment: IATA PI 969 (packed with) or PI 970 (contained in).",
    },
    "3551": {
        "iata_packing_instruction": "976",
        "note_nl": "Natrium-ionbatterijen met organisch elektrolyt (los verpakt): IATA PI 976. Natrium-ionbatterijen met waterig alkalisch elektrolyt vallen onder UN 2795 (accu's, nat, gevuld met alkali).",
        "note_en": "Sodium ion batteries with organic electrolyte (packed by themselves): IATA PI 976. Sodium-ion batteries with aqueous alkali electrolyte fall under UN 2795 (batteries, wet, filled with alkali).",
    },
    "3552": {
        "iata_packing_instruction": "977/978",
        "note_nl": "Natrium-ionbatterijen met of in apparatuur: IATA PI 977 (met apparatuur) of PI 978 (in apparatuur).",
        "note_en": "Sodium ion batteries packed with or contained in equipment: IATA PI 977 (packed with) or PI 978 (contained in).",
    },
    "3556": {
        "note_nl": "Voertuig aangedreven door een lithium-ionbatterij: bij een batterij van meer dan 100 Wh gelden de volledige voorschriften voor voertuigen op batterijen.",
        "note_en": "Vehicle powered by a lithium-ion battery: with a battery exceeding 100 Wh the full provisions for battery-powered vehicles apply.",
    },
    "3557": {
        "note_nl": "Voertuig aangedreven door een lithium-metaalbatterij: bij een batterij van meer dan 100 Wh gelden de volledige voorschriften voor voertuigen op batterijen.",
        "note_en": "Vehicle powered by a lithium metal battery: with a battery exceeding 100 Wh the full provisions for battery-powered vehicles apply.",
    },
    "3558": {
        "note_nl": "Voertuig aangedreven door een natrium-ionbatterij: bij een batterij van meer dan 100 Wh gelden de volledige voorschriften voor voertuigen op batterijen.",
        "note_en": "Vehicle powered by a sodium ion battery: with a battery exceeding 100 Wh the full provisions for battery-powered vehicles apply.",
    },
}

# Klassen die in de luchtvaart (vrijwel altijd) verboden zijn.
AIR_FORBIDDEN_CLASSES = {"2.3"}

# UN-nummers die per definitie milieugevaarlijk zijn; classificatiecodes M6/M7
# (ADR) markeren milieugevaarlijke stoffen van klasse 9 (IMDG: marine pollutant).
ENVIRONMENTALLY_HAZARDOUS_UN = {"3077", "3082"}
ENVIRONMENTALLY_HAZARDOUS_CODES = {"M6", "M7"}


# Aanvullende documentvereisten die niet uit Tabel A af te leiden zijn en die
# de gebruiker zelf moet aanleveren (ADR/RID/ADN 5.4.1.1, IMDG 5.4.1, IATA 8.1.6).
CLASS_DOCUMENT_NOTES: dict[str, dict[str, str]] = {
    "1": {
        "nl": "Klasse 1: vermeld in het vervoersdocument de totale netto explosieve massa (NEM) per stof en, bij samenlading, de compatibiliteitsgroepen (ADR 5.4.1.2.1).",
        "en": "Class 1: state the total net explosive mass (NEM) per substance in the transport document and, when mixed, the compatibility groups (ADR 5.4.1.2.1).",
    },
    "2": {
        "nl": "Klasse 2: bij tankvervoer en drukhouders horen de vuldatum, beproevingsdatum en het toegestane vulgewicht bij de zending (ADR 5.4.1.2.2).",
        "en": "Class 2: for tanks and pressure receptacles the filling date, test date and permitted filling mass accompany the consignment (ADR 5.4.1.2.2).",
    },
    "4.1": {
        "nl": "Zelfontledende stoffen en gedesensibiliseerde explosieven: vermeld de temperatuurbeheersing (controle- en noodtemperatuur) wanneer die geldt (ADR 5.4.1.2.3.1).",
        "en": "Self-reactive substances and desensitized explosives: state the control and emergency temperature where applicable (ADR 5.4.1.2.3.1).",
    },
    "5.2": {
        "nl": "Organische peroxiden: vermeld de controle- en noodtemperatuur wanneer temperatuurbeheersing is voorgeschreven (ADR 5.4.1.2.3.1).",
        "en": "Organic peroxides: state the control and emergency temperature where temperature control is required (ADR 5.4.1.2.3.1).",
    },
    "6.2": {
        "nl": "Klasse 6.2: vermeld naam en telefoonnummer van een verantwoordelijke persoon in het vervoersdocument (ADR 5.4.1.2.4).",
        "en": "Class 6.2: state the name and telephone number of a responsible person in the transport document (ADR 5.4.1.2.4).",
    },
    "7": {
        "nl": "Klasse 7: het vervoersdocument vereist aanvullend de radionucliden, fysische en chemische vorm, maximale activiteit, collo-categorie (I-WIT/II-GEEL/III-GEEL), transportindex en waar van toepassing de veiligheidsindex kritikaliteit (ADR 5.4.1.2.5.1).",
        "en": "Class 7: the transport document additionally requires the radionuclides, physical and chemical form, maximum activity, package category (I-WHITE/II-YELLOW/III-YELLOW), transport index and, where applicable, the criticality safety index (ADR 5.4.1.2.5.1).",
    },
}

# Aanvullende vereisten per modaliteitsprofiel.
PROFILE_DOCUMENT_NOTES: dict[str, dict[str, str]] = {
    "IMDG": {
        "nl": "Zeevervoer: het containerbeladingscertificaat (CTU-packing certificate) hoort bij de zending, en bij containers over zee geldt de geverifieerde bruto massa (VGM, SOLAS VI/2).",
        "en": "Sea transport: the container/vehicle packing certificate accompanies the consignment, and containers require a verified gross mass (VGM, SOLAS VI/2).",
    },
    "IATA_DGR": {
        "nl": "Luchtvervoer: de Shipper's Declaration wordt in tweevoud ondertekend aangeleverd en de hoeveelheden per collo mogen de limieten van de gekozen verpakkingsinstructie niet overschrijden.",
        "en": "Air transport: the Shipper's Declaration is provided signed in duplicate and quantities per package must not exceed the limits of the applicable packing instruction.",
    },
}


def _norm_un(un: str) -> str:
    return "".join(ch for ch in str(un or "") if ch.isdigit()).zfill(4)


# ADR Tabel A vult bij verboden stoffen élke kolom met deze tekst; die mag
# nooit als gegevenswaarde in een formulier of documentregel terechtkomen.
FORBIDDEN_MARKER = "VERBOTEN"


def clean_value(value: Any) -> str:
    """Lege string voor kolommen die alleen het vervoersverbod herhalen."""
    text = str(value or "").strip()
    return "" if FORBIDDEN_MARKER in text.upper() else text


def _norm_label(token: str) -> str:
    """'9A' → '9', '2.3' → '2.3'; etiketmodelletters horen niet bij de klasse."""
    token = token.strip().upper()
    match = re.match(r"^(\d(?:\.\d)?)", token)
    return match.group(1) if match else token


def parse_hazards(entry: dict[str, Any]) -> dict[str, Any]:
    """Leid hoofdgevaar (incl. divisie) en nevengevaren af uit ADR Tabel A.

    De kolom 'klasse' geeft bij gassen alleen '2' en bij explosieven alleen '1';
    de werkelijke divisie staat in de etikettenkolom respectievelijk de
    classificatiecode (bijv. '1.4S'). Nevengevaren zijn de etiketten ná het
    eerste — de classificatiecode (F1, M4, C1) is géén nevengevaar.
    """
    hazard_class = str(entry.get("class") or "").strip()
    classification = str(entry.get("classification_code") or "").strip().upper()
    raw_labels = clean_value(entry.get("labels"))
    tokens = [_norm_label(t) for t in raw_labels.split("+") if t.strip()]

    division = hazard_class
    if hazard_class == "1" and re.match(r"^1\.\d[A-S]$", classification):
        division = classification  # bijv. 1.4S — bepalend voor samenlading
    elif tokens and tokens[0].startswith(f"{hazard_class}."):
        division = tokens[0]  # bijv. gassen: klasse 2 → divisie 2.1/2.2/2.3
    elif not hazard_class and tokens:
        division = tokens[0]

    subsidiary = [t for t in tokens[1:] if t and t != division]
    return {
        "division": division,
        "subsidiary_risks": subsidiary,
        "classification_code": classification,
        "labels": raw_labels,
    }


def describe_excepted_quantity(code: str, language: str = "nl") -> str | None:
    code = (code or "").strip().upper()
    if code == "E0":
        return (
            "E0: niet toegestaan als vrijgestelde hoeveelheid"
            if language == "nl"
            else "E0: not permitted as excepted quantity"
        )
    limits = EXCEPTED_QUANTITY_LIMITS.get(code)
    if not limits:
        return None
    inner, outer = limits
    if language == "nl":
        return f"{code}: max. {inner} g/ml per binnenverpakking, {outer} g/ml per buitenverpakking"
    return f"{code}: max. {inner} g/ml per inner packaging, {outer} g/ml per outer packaging"


def enrich_un_entry(entry: dict[str, Any], language: str = "nl") -> dict[str, Any]:
    """Afleidbare gegevens per modaliteit voor een offline UN-vermelding.

    Retourneert alleen velden die met voldoende zekerheid afgeleid kunnen
    worden; indicatieve waarden worden expliciet gemarkeerd zodat de
    interface ze als suggestie kan tonen in plaats van ze in te vullen.
    """
    un = _norm_un(entry.get("un", entry.get("un_number", "")))
    hazard_class = str(entry.get("class") or "").strip()
    classification = str(entry.get("classification_code") or "").strip().upper()
    extras: dict[str, Any] = {}

    # Vervoersverbod: ADR Tabel A vermeldt "BEFÖRDERUNG VERBOTEN" in de
    # etikettenkolom voor stoffen die niet ten vervoer mogen worden aangeboden.
    labels_raw = str(entry.get("labels") or "")
    if "VERBOTEN" in labels_raw.upper():
        extras["transport_forbidden"] = True
        extras["transport_forbidden_note"] = (
            "Deze stof mag volgens ADR Tabel A niet ten vervoer worden aangeboden. "
            "Vervoer is uitsluitend mogelijk onder een ontheffing van de bevoegde autoriteit."
            if language == "nl"
            else "Per ADR Table A this substance is not permitted for carriage. "
            "Carriage is only possible under an exemption from the competent authority."
        )
    if "5.2.2.1.12" in labels_raw:
        extras["label_reference_note"] = (
            "Etikettering volgens 5.2.2.1.12: voorwerpen die gevaarlijke goederen bevatten "
            "krijgen de etiketten van elk aanwezig gevaar."
            if language == "nl"
            else "Labelling per 5.2.2.1.12: articles containing dangerous goods bear the "
            "labels for each hazard present."
        )

    # Scheidingsgroepen (IMDG 3.1.4.4): bepalend voor de scheiding aan boord.
    sgg = segregation_groups_for(un)
    if sgg:
        extras["segregation_groups"] = sgg
        extras["segregation_groups_text"] = ", ".join(
            f"{code} ({segregation_group_label(code, language)})" for code in sgg
        )

    # Zeevaart (IMDG): EmS uit de officiële EmS Guide-index.
    ems = lookup_ems(un, clean_value(entry.get("packing_group")))
    if ems and ems.get("fire"):
        extras["ems_code"] = f"{ems['fire']}, {ems['spillage']}"
        extras["ems_source"] = "ems_guide"
        extras["ems_description"] = describe_ems(extras["ems_code"], language)
    elif ems and ems.get("variants"):
        extras["ems_variants"] = [
            {
                "label": item["label"],
                "code": f"{item['fire']}, {item['spillage']}",
                "description": describe_ems(f"{item['fire']}, {item['spillage']}", language),
            }
            for item in ems["variants"]
        ]
        extras["ems_source"] = "ems_guide_variants"
    elif ems and ems.get("packing_group_options"):
        extras["ems_packing_group_options"] = {
            pg: f"{v['fire']}, {v['spillage']}" for pg, v in ems["packing_group_options"].items()
        }
        extras["ems_source"] = "ems_guide_packing_group"
    else:
        # Terugval op de divisie (2.1/2.3) en anders op de hoofdklasse.
        division = str(entry.get("labels") or "").split("+")[0].strip() or hazard_class
        default = EMS_DEFAULT_BY_CLASS.get(division) or EMS_DEFAULT_BY_CLASS.get(hazard_class)
        if default:
            extras["ems_class_default"] = f"{default[0]}, {default[1]}"
            extras["ems_source"] = "class_default"

    # Stof-specifieke IMDG-gegevens van de UN-kaart (41-22), bijgewerkt met de
    # wijzigingen van Amendment 42-24 — sinds 1 januari 2026 de verplichte editie.
    packing_group = clean_value(entry.get("packing_group"))
    card = amendment_42_24.apply_card_overlay(un, card_data_for(un), packing_group)
    if card:
        extras["card_source"] = "imdg_un_card"

        # Marine pollutant, kolom 4. De bron zegt bij n.e.g.-vermeldingen
        # "maybe": dat hangt van de werkelijke stof af en is aan de afzender.
        pollutant = card.get("marine_pollutant")
        if pollutant in {"yes", "no", "maybe"}:
            extras["marine_pollutant_status"] = pollutant
            extras["marine_pollutant_text"] = _MARINE_POLLUTANT_TEXT[language == "nl"][pollutant]
            if pollutant == "yes":
                extras["environmentally_hazardous"] = True

        # Stuwage (16a) en scheiding (16b): de codes plus de toelichting van de
        # kaart, want "SG35" zegt op zichzelf niets tegen een gebruiker.
        if card.get("stowage_codes"):
            extras["imdg_stowage_codes"] = card["stowage_codes"]
            described = describe_imdg_codes(card["stowage_codes"])
            if described:
                extras["imdg_stowage_definitions"] = described
        if card.get("segregation_codes"):
            extras["imdg_segregation_codes"] = card["segregation_codes"]
            described = describe_imdg_codes(card["segregation_codes"])
            if described:
                extras["imdg_segregation_definitions"] = described
        for field, key in (("stowage_text", "imdg_stowage_text"),
                           ("segregation_text", "imdg_segregation_text")):
            value = card.get(field)
            if isinstance(value, str) and value.strip():
                extras[key] = value.strip()

        bulk = str(card.get("bulk") or "")
        if "bk" in bulk:
            extras["imdg_bulk"] = bulk.upper().replace("BK", "BK")
        elif bulk:
            extras["imdg_bulk_forbidden"] = True

        if card.get("stowage_category"):
            extras["imdg_stowage_category"] = card["stowage_category"]

    # Wat Amendment 42-24 aan deze stof verandert. Dit staat los van de kaart:
    # ook stoffen zonder kaart (of nieuw in 42-24) kunnen wijzigingen hebben.
    changes = amendment_42_24.changes_for(un, packing_group, language)
    if changes:
        extras["imdg_amendment_changes"] = changes
        extras["imdg_amendment"] = amendment_42_24.amendment()
    doc_requirement = amendment_42_24.document_requirement(un, language)
    if doc_requirement:
        extras["imdg_document_requirement"] = doc_requirement

    # Milieugevaarlijk / marine pollutant — ADR-kant, blijft ook zonder kaart gelden.
    if un in ENVIRONMENTALLY_HAZARDOUS_UN or classification in ENVIRONMENTALLY_HAZARDOUS_CODES:
        extras["environmentally_hazardous"] = True

    # Luchtvracht (IATA/ICAO)
    air = AIR_RULES_BY_UN.get(un)
    if air:
        if air.get("cargo_aircraft_only"):
            extras["cargo_aircraft_only"] = True
        if air.get("iata_packing_instruction"):
            extras["iata_packing_instruction"] = air["iata_packing_instruction"]
        extras["air_note"] = air.get(f"note_{language}") or air.get("note_nl")
    if hazard_class in AIR_FORBIDDEN_CLASSES:
        extras["air_forbidden"] = True
        extras["air_note"] = (
            "Klasse 2.3 (giftige gassen) is in de luchtvaart verboden, op enkele uitzonderingen na."
            if language == "nl"
            else "Division 2.3 (toxic gases) is forbidden in air transport, with few exceptions."
        )

    # Vrijgestelde hoeveelheden uitleggen
    eq_text = describe_excepted_quantity(clean_value(entry.get("excepted_quantity")), language)
    if eq_text:
        extras["excepted_quantity_text"] = eq_text

    lq = clean_value(entry.get("limited_quantity"))
    if lq and lq != "0":
        extras["limited_quantity_text"] = (
            f"LQ: max. {lq} per binnenverpakking (ADR/IMDG 3.4)"
            if language == "nl"
            else f"LQ: max. {lq} per inner packaging (ADR/IMDG 3.4)"
        )

    return extras
