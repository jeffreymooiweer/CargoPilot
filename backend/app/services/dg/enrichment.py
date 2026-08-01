"""Verrijking van UN-vermeldingen voor automatische invulling per modaliteit.

Feitencompilatie als invulhulp; de actuele uitgave van ADR/RID/ADN, de IMDG-code
en de IATA DGR blijft altijd leidend. Bronnen:
- EmS per UN-nummer: IMDG-code Dangerous Goods List (kolom 15), gecureerde
  selectie van veelvervoerde stoffen; overige klassen krijgen een indicatieve
  klassestandaard die als zodanig wordt gemarkeerd.
- Vrijgestelde hoeveelheden (E-codes): ADR/IMDG/IATA 3.5.1.2.
- Luchtvrachtregels: IATA DGR (lithiumbatterijen PI 965/968 — Cargo Aircraft
  Only), ICAO TI (klasse 2.3 verboden in luchtvracht).
- Milieugevaarlijk/marine pollutant: UN 3077/3082 en ADR-classificatiecodes
  M6/M7 (IMDG 2.10).
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

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


def lookup_ems(un_number: str) -> dict[str, Any] | None:
    """EmS-vermelding voor een UN-nummer, of None wanneer die ontbreekt."""
    digits = "".join(ch for ch in str(un_number or "") if ch.isdigit()).zfill(4)
    return _load_ems()["entries"].get(digits)


def ems_profile_label(profile: str, language: str = "nl") -> str:
    labels = _load_ems()["profiles"].get(profile) or {}
    return labels.get(language) or labels.get("nl") or ""


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

# Luchtvrachtregels per UN-nummer (IATA DGR / ICAO TI).
AIR_RULES_BY_UN: dict[str, dict[str, Any]] = {
    "3480": {
        "cargo_aircraft_only": True,
        "iata_packing_instruction": "965",
        "note_nl": "Lithium-ionbatterijen (los): uitsluitend Cargo Aircraft Only, IATA PI 965, laadtoestand max. 30% (SoC).",
        "note_en": "Lithium-ion batteries (standalone): Cargo Aircraft Only, IATA PI 965, state of charge max. 30%.",
    },
    "3090": {
        "cargo_aircraft_only": True,
        "iata_packing_instruction": "968",
        "note_nl": "Lithium-metaalbatterijen (los): uitsluitend Cargo Aircraft Only, IATA PI 968.",
        "note_en": "Lithium metal batteries (standalone): Cargo Aircraft Only, IATA PI 968.",
    },
    "3481": {
        "iata_packing_instruction": "966/967",
        "note_nl": "Lithium-ionbatterijen met/in apparatuur: IATA PI 966 (met) of 967 (in apparatuur).",
        "note_en": "Lithium-ion batteries packed with/contained in equipment: IATA PI 966/967.",
    },
    "3091": {
        "iata_packing_instruction": "969/970",
        "note_nl": "Lithium-metaalbatterijen met/in apparatuur: IATA PI 969 (met) of 970 (in apparatuur).",
        "note_en": "Lithium metal batteries packed with/contained in equipment: IATA PI 969/970.",
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

    # Zeevaart (IMDG): EmS
    ems = lookup_ems(un)
    if ems:
        extras["ems_code"] = f"{ems['fire']}, {ems['spillage']}"
        extras["ems_source"] = "imdg_dgl"
        extras["ems_verified"] = bool(ems.get("verified"))
        label = ems_profile_label(ems.get("profile", ""), language)
        if label:
            extras["ems_profile"] = label
    else:
        # Terugval op de divisie (2.1/2.3) en anders op de hoofdklasse.
        division = str(entry.get("labels") or "").split("+")[0].strip() or hazard_class
        default = EMS_DEFAULT_BY_CLASS.get(division) or EMS_DEFAULT_BY_CLASS.get(hazard_class)
        if default:
            extras["ems_class_default"] = f"{default[0]}, {default[1]}"
            extras["ems_source"] = "class_default"

    # Milieugevaarlijk / marine pollutant
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
