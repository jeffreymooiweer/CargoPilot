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
from app.services.dg.naming import (
    ENGLISH_ONLY_PROFILES,
    proper_shipping_name,
    resolve_for_profile,
)
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


#: Kilograms before litres, because "kilogram" and "kilo" both contain an "l"
#: and would otherwise be read as litres. The lookarounds are letter-only rather
#: than `\b`: a word boundary does not fire between a digit and a letter, so
#: "100L" — which is how people type it — would have fallen through to the
#: default and become kilograms.
_KILOGRAMS = re.compile(r"(?<![a-z])(kg|kilo(?:gram)?s?)(?![a-z])", re.IGNORECASE)
_LITRES = re.compile(r"(?<![a-z])(l|ltr|lit(?:er|re)s?)(?![a-z])", re.IGNORECASE)


def _unit_of(raw: Any) -> str:
    """The unit written in a quantity, or nothing at all.

    Nothing means nothing: this deliberately does not fall back to kilograms.
    Whether a substance travels by mass or by volume is not reliably derivable
    from table A, and a unit invented here ends up on a signed consignment note
    — 100 litres of acetone is about 79 kg, and 1.1.3.6.3 counts the two
    differently. An absent unit is reported to the user instead (ADR
    5.4.1.1.1 (f)).
    """
    text = str(raw or "")
    if _KILOGRAMS.search(text):
        return "kg"
    if _LITRES.search(text):
        return "L"
    return ""


def _amount(value: float, unit: str) -> str:
    """A quantity for a document: the number, and the unit only if there is one."""
    return f"{_fmt(value)} {unit}".strip()


def _un_prefixed(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.upper().startswith(("UN", "ID")) else f"UN {text}"


#: The columns of Table A that differ between the rows of one UN number and that
#: the application fills in from them. Two rows that agree on all of these are
#: interchangeable for everything CargoPilot derives, and choosing between them
#: is not worth a word to the user.
TABLE_A_VARIANT_FIELDS = (
    "packing_group",
    "classification_code",
    "labels",
    "transport_category",
    "tunnel_code",
    "limited_quantity",
    "excepted_quantity",
    "hazard_number",
    "packing_instructions",
)

#: How each of those columns is named to the user. Short, because they end up in
#: one sentence together.
TABLE_A_FIELD_LABELS: dict[str, dict[str, str]] = {
    "packing_group": {"nl": "verpakkingsgroep", "en": "packing group",
                      "de": "Verpackungsgruppe", "fr": "groupe d'emballage"},
    "classification_code": {"nl": "classificatiecode", "en": "classification code",
                            "de": "Klassifizierungscode", "fr": "code de classification"},
    "labels": {"nl": "etiketten", "en": "labels", "de": "Gefahrzettel",
               "fr": "étiquettes"},
    "transport_category": {"nl": "vervoerscategorie", "en": "transport category",
                           "de": "Beförderungskategorie", "fr": "catégorie de transport"},
    "tunnel_code": {"nl": "tunnelcode", "en": "tunnel code", "de": "Tunnelcode",
                    "fr": "code tunnel"},
    "limited_quantity": {"nl": "LQ", "en": "LQ", "de": "LQ", "fr": "QL"},
    "excepted_quantity": {"nl": "E-code", "en": "E code", "de": "E-Code",
                          "fr": "code E"},
    "hazard_number": {"nl": "gevaarsidentificatienummer", "en": "hazard identification No.",
                      "de": "Gefahrnummer", "fr": "numéro d'identification du danger"},
    "packing_instructions": {"nl": "verpakkingsinstructie", "en": "packing instruction",
                             "de": "Verpackungsanweisung", "fr": "instruction d'emballage"},
}

#: The two shapes of the variant note: one that can name a field to enter, and
#: one for the rows no field the user fills in can tell apart.
_VARIANT_NOTE = {
    "nl": "UN {un} heeft {count} rijen in tabel A die verschillen in {fields}. Rij "
          "{chosen} is voorlopig ingevuld. Vul de {settle} in om de juiste rij te "
          "kiezen: {variants}.",
    "en": "UN {un} has {count} rows in Table A differing in {fields}. Row {chosen} was "
          "filled in provisionally. Enter the {settle} to pick the right one: {variants}.",
    "de": "UN {un} hat {count} Zeilen in Tabelle A, die sich in {fields} unterscheiden. "
          "Zeile {chosen} wurde vorläufig eingetragen. Geben Sie die {settle} ein, um die "
          "richtige zu wählen: {variants}.",
    "fr": "L'ONU {un} a {count} lignes au tableau A qui diffèrent par {fields}. La ligne "
          "{chosen} a été remplie à titre provisoire. Indiquez le {settle} pour choisir "
          "la bonne : {variants}.",
}

_VARIANT_NOTE_UNRESOLVABLE = {
    "nl": "UN {un} heeft {count} rijen in tabel A die verschillen in {fields}. Rij "
          "{chosen} is voorlopig ingevuld; classificatiecode en verpakkingsgroep zijn "
          "voor alle rijen gelijk, dus controleer zelf welke van deze op uw zending "
          "slaat: {variants}.",
    "en": "UN {un} has {count} rows in Table A differing in {fields}. Row {chosen} was "
          "filled in provisionally; the classification code and packing group are the "
          "same for every row, so check for yourself which of these describes your "
          "consignment: {variants}.",
    "de": "UN {un} hat {count} Zeilen in Tabelle A, die sich in {fields} unterscheiden. "
          "Zeile {chosen} wurde vorläufig eingetragen; Klassifizierungscode und "
          "Verpackungsgruppe sind für alle Zeilen gleich, prüfen Sie daher selbst, welche "
          "auf Ihre Sendung zutrifft: {variants}.",
    "fr": "L'ONU {un} a {count} lignes au tableau A qui diffèrent par {fields}. La ligne "
          "{chosen} a été remplie à titre provisoire ; le code de classification et le "
          "groupe d'emballage sont identiques pour toutes les lignes, vérifiez donc "
          "vous-même laquelle correspond à votre envoi : {variants}.",
}


def _same_value(value: Any, given: str) -> bool:
    return clean_value(value).strip().upper() == given


def select_table_a_row(
    entries: list[dict[str, Any]], product: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The Table A row to fill from, and the rows that were still in the running.

    Until v1.51.0 this looked at the packing group only, and where every row had
    the same one — or none — the first row was taken in silence. That is not a
    marginal case. **UN 1950, aerosols, has twelve rows in Table A** and they all
    have no packing group: 5A is non-flammable, transport category 3, tunnel code
    E; 5F is flammable (2.1), category 2, tunnel code D; 5T is toxic, category 1.
    A user shipping ordinary flammable spray cans was given the row for the
    non-flammable ones — a points factor three times too low, the wrong tunnel
    code and no flammability label — without a word about it. UN 2037, gas
    cartridges, has nine rows and the same problem, and UN 0015, 0016 and 0303
    differ only in whether the ammunition carries a corrosive or a toxic label.

    What tells the rows apart in ADR is the **classification code** of column
    (3b): 5A, 5F, 5T, 1.2G. So that is looked at first, then the packing group.
    Whatever the user has filled in narrows the field; what is left over is
    returned so the caller can say that a choice is still open.
    """
    candidates = list(entries)
    for field in ("classification_code", "packing_group"):
        given = str(product.get(field) or "").strip().upper()
        if not given:
            continue
        narrowed = [e for e in candidates if _same_value(e.get(field), given)]
        if narrowed:
            candidates = narrowed
    return (candidates[0] if candidates else entries[0]), candidates


def table_a_variant_note(
    entry: dict[str, Any], candidates: list[dict[str, Any]], language: str = "nl"
) -> str | None:
    """What the rows still in the running differ in, and how to choose between them.

    A note that only said "there are several packing groups" could not describe
    UN 1950 at all, because its twelve rows have no packing group. This one names
    the columns that actually differ and lists the alternatives by their
    classification code, which is the field the user can enter to settle it.
    """
    if len(candidates) < 2:
        return None
    differing = [
        field for field in TABLE_A_VARIANT_FIELDS
        if len({clean_value(e.get(field)).strip().upper() for e in candidates}) > 1
    ]
    if not differing:
        # Rows that agree on everything the application uses. UN 1202 has three
        # of them, apart from a special provision it does not compute with.
        return None

    def describe(row: dict[str, Any]) -> str:
        code = clean_value(row.get("classification_code")).strip().upper()
        pg = clean_value(row.get("packing_group")).strip().upper()
        head = " ".join(part for part in (code, f"VG {pg}" if pg else "") if part) or "?"
        detail = ", ".join(
            f"{pick(TABLE_A_FIELD_LABELS[field], language)} "
            f"{clean_value(row.get(field)) or '—'}"
            for field in differing
            if field not in ("classification_code", "packing_group")
        )
        return f"{head} ({detail})" if detail else head

    # What to tell the user to enter. The classification code settles it for UN
    # 1950 and UN 2037, but not for UN 0015, whose three rows are all 1.2G and
    # differ only in the label. Naming a field that does not discriminate is
    # worse than naming none.
    key = next((field for field in ("classification_code", "packing_group")
                if field in differing), None)
    template = _VARIANT_NOTE if key else _VARIANT_NOTE_UNRESOLVABLE
    return pick(template, language).format(
        settle=pick(TABLE_A_FIELD_LABELS[key], language) if key else "",
        un=clean_value(entry.get("un")),
        count=len(candidates),
        fields=", ".join(pick(TABLE_A_FIELD_LABELS[field], language)
                         for field in differing),
        chosen=describe(entry),
        variants="; ".join(describe(row) for row in candidates),
    )


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

    # One UN number can have several Table A rows, and picking the wrong one is
    # not a detail: it changes the transport category (and with it the points
    # factor), the tunnel code, the labels and the LQ. What the user has already
    # filled in narrows the choice — the classification code first, because that
    # is the column ADR uses to tell the rows apart.
    entry, candidates = select_table_a_row(entries, product)

    extras = enrich_un_entry(entry, language)
    hazards = parse_hazards(entry)

    derived: dict[str, Any] = {
        "proper_shipping_name": proper_shipping_name(entry, language, profiles),
        "class": hazards["division"],
        "subsidiary_risks": ", ".join(hazards["subsidiary_risks"]),
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

    # More than one row still in the running: the first was filled in, and that
    # was a choice nobody made. It has to be said, and it has to say what the
    # rows differ in — otherwise the user cannot tell whether it matters.
    note = table_a_variant_note(entry, candidates, language)
    if note:
        hints["table_a_variant_note"] = note
        # Kept under the old key as well: the interface, the export and the
        # tests all read that one, and a note nobody renders is no note.
        hints["packing_group_note"] = note

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
    """Total quantity of a product: net per package × number of packages.

    The unit is read from **the same field the number came from**. It used to be
    read from the per-package field alone, which is right while that field is
    filled and wrong the moment it is empty: the number then fell back to
    `adr_total_quantity` while the unit stayed on its "kg" default, so "100 L"
    came out as "100 kg" — on the document, in the category totals of
    5.4.1.1.1.1, and written back over what the user had typed.

    That is not a corner: the wizard requires only UN number, name and class for
    ADR, RID and ADN, so a consignor who fills in nothing but the total quantity
    the 1.1.3.6 points count needs takes this path every time.
    """
    per_package = _num(product.get("net_mass_liters_per_package"))
    count = _num(product.get("quantity_packages"))
    if per_package is None:
        raw_total = product.get("adr_total_quantity")
        return _num(raw_total), _unit_of(raw_total)
    unit = _unit_of(product.get("net_mass_liters_per_package"))
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


#: The modes of carriage for which RID 5.3.2.1.1 prescribes the orange plate,
#: and therefore the modes in which RID 5.4.1.1.1 (j) puts the hazard
#: identification number on the transport document. Read twice — the English
#: edition on printed page 5-27 and the German on 5-27 of its own numbering —
#: which list tank-wagons, battery-wagons, wagons with demountable tanks,
#: tank-containers, MEGCs, portable tanks and wagons or containers for carriage
#: in bulk. For a full load of packages of one and the same substance the plate
#: *may* be affixed rather than shall, and whether it was is not something this
#: application can see; that case is reported instead (see check_rid_hazard_id).
_RID_MARKED_MODES = {"tank", "portable_tank", "bulk"}


def rid_marking_prescribed(product: dict[str, Any]) -> bool:
    """Whether RID 5.3.2.1 marking is prescribed for how these goods travel."""
    return str(product.get("carriage_mode") or "").strip() in _RID_MARKED_MODES


#: The words 5.4.1.1.3, 5.4.1.1.5, 5.4.1.1.6.1 and 5.4.1.1.18 put on the
#: document, in the languages this application writes documents in. Read in the
#: official Dutch edition (pages 991-996), the RID English and German editions
#: (846/906 — the provisions are shared word for word) and the UNECE English
#: and French volumes II. These are document entries, not interface strings:
#: the regulation prescribes the word itself, so it follows the language of the
#: document under 5.4.1.4.1 and is always English where the document must be
#: (IMDG 5.4.1.4.1, IATA DGR 8.1.2.1).
_WASTE_WORD = {
    "nl": "AFVAL", "en": "WASTE", "de": "ABFALL", "fr": "DÉCHET"}
_EMPTY_UNCLEANED = {
    "nl": "LEEG, ONGEREINIGD", "en": "EMPTY, UNCLEANED",
    "de": "LEER, UNGEREINIGT", "fr": "VIDE, NON NETTOYÉ"}
_SALVAGE = {
    "packaging": {
        "nl": "BERGINGSVERPAKKING", "en": "SALVAGE PACKAGING",
        "de": "BERGUNGSVERPACKUNG", "fr": "EMBALLAGE DE SECOURS"},
    "pressure_receptacle": {
        "nl": "BERGINGSDRUKHOUDER", "en": "SALVAGE PRESSURE RECEPTACLE",
        "de": "BERGUNGSDRUCKGEFÄSS", "fr": "RÉCIPIENT À PRESSION DE SECOURS"},
}
_ENVIRONMENTALLY_HAZARDOUS = {
    "nl": "MILIEUGEVAARLIJK", "en": "ENVIRONMENTALLY HAZARDOUS",
    "de": "UMWELTGEFÄHRDEND", "fr": "DANGEREUX POUR L'ENVIRONNEMENT"}

#: 5.4.1.1.18's own exception: the names of UN 3077 and 3082 already say it,
#: and the additional entry is expressly not required for them.
_ENV_SELF_EVIDENT = {"3077", "3082"}


def _document_word(words: dict[str, str], profile: str, language: str) -> str:
    """The regulation's word in the language of *this* document."""
    if profile in ENGLISH_ONLY_PROFILES:
        return words["en"]
    return words.get((language or "nl").split("-")[0].lower(), words["en"])


def description_line(product: dict[str, Any], profile: str, language: str = "",
                     values: dict[str, Any] | None = None) -> str:
    """Official description line for the transport document.

    One builder for every caller. The exporter used to compose its own, and two
    renderings of one provision drift the moment either is corrected: the
    subsidiary label models and the hazard identification number below would
    have reached the wizard and not the CMR.
    """
    values = values or {}
    # The name follows the document: on an IMDG or IATA line it should be
    # English, even when the consignment was drawn up in German (IMDG 5.4.1.4.1,
    # IATA DGR 8.1.2.1).
    psn = resolve_for_profile(product, profile, language)[0].upper()
    # 5.4.1.1.3: waste containing dangerous goods carries the word before the
    # proper shipping name, unless the name already says it — the provision's
    # own example is "UN 1230 AFVAL METHANOL, 3 (6.1), II, (D/E)".
    if product.get("is_waste"):
        word = _document_word(_WASTE_WORD, profile, language)
        if word not in psn:
            psn = f"{word} {psn}"
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
        tunnel = str(values.get("tunnel_restriction")
                     or product.get("tunnel_code") or "").strip().strip("()")
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

    # RID 5.4.1.1.1 (j), and rail alone. Where a marking under 5.3.2.1 is
    # prescribed, the hazard identification number goes *before* the letters
    # "UN", and the text is explicit about the order: (j), (a), (b), (c), (d)
    # with no information interspersed. Its own example is
    # "663, UN 1098 ALLYL ALCOHOL, 6.1(3), I". The ADR has no such paragraph —
    # its (k) is the tunnel restriction code — so a number in front of a CMR
    # would be an entry nobody asked for.
    if profile == "RID" and rid_marking_prescribed(product):
        hazard_number = str(product.get("hazard_number") or "").strip()
        if hazard_number:
            line = f"{hazard_number}, {line}"

    # 5.4.1.1.6.1: an empty means of containment, uncleaned, carrying residues
    # of anything but class 7, says so before or after the description — and
    # 5.4.1.1.1 (f) then does not apply, so no total quantity is composed for
    # residues nobody has weighed. The fuller substitutions of 5.4.1.1.6.2 are
    # permissions, not requirements ("may be replaced"); the form always
    # allowed is the one composed.
    empty_uncleaned = bool(product.get("empty_uncleaned"))
    if empty_uncleaned:
        line = f"{line}, {_document_word(_EMPTY_UNCLEANED, profile, language)}"

    # 5.4.1.1.5: goods travelling in a salvage packaging or salvage pressure
    # receptacle carry the word after the description of the goods.
    salvage = str(product.get("salvage_packaging") or "").strip().lower()
    if salvage:
        words = _SALVAGE.get(salvage, _SALVAGE["packaging"])
        line = f"{line}, {_document_word(words, profile, language)}"

    # 5.4.1.1.18: a substance meeting 2.2.9.1.10 carries the additional entry —
    # except UN 3077 and 3082, whose names already say it, and except at sea,
    # where "MARINE POLLUTANT" (which the IMDG branch above already adds) is
    # the entry the provision itself points at.
    if (profile in ("ADR", "RID", "ADN")
            and (product.get("environmentally_hazardous")
                 or str(product.get("marine_pollutant") or "").strip().upper()
                 in {"P", "Y", "YES", "JA", "TRUE", "1"})):
        un_digits = "".join(
            c for c in str(product.get("un_number") or "") if c.isdigit()).zfill(4)
        if un_digits not in _ENV_SELF_EVIDENT:
            line = (f"{line}, "
                    f"{_document_word(_ENVIRONMENTALLY_HAZARDOUS, profile, language)}")

    # Number and type of packages + total quantity (ADR 5.4.1.1.1 f/g).
    count = str(product.get("quantity_packages") or "").strip()
    package = str(product.get("type_of_package") or "").strip()
    packages = " ".join(p for p in [count, package] if p)
    total, unit = total_quantity(product)
    tail = []
    if packages:
        tail.append(packages)
    if total is not None and not empty_uncleaned:
        tail.append(_amount(total, unit))
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
        amounts = ", ".join(_amount(value, unit) for unit, value in sorted(totals[category].items()))
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
                merged["adr_total_quantity"] = _amount(total, unit)
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
