"""IMDG-code Amendment 42-24: de verschillenlaag en de voorrangsregel 7.2.3.1.

De app draagt ADR 2025 als basistabel en de UN-kaarten van 41-22 als
stof-specifieke IMDG-laag. Sinds 1 januari 2026 is 42-24 verplicht. Deze tests
leggen vast wat de laag doet — en, minstens zo belangrijk, wat zij niet doet:
zij past nooit stilzwijgend een classificatie aan en haalt nooit een melding weg.
"""

import json
from pathlib import Path

import pytest

from app.services.dg import amendment_42_24
from app.services.dg.compliance import apply_column_16b_precedence, check_compliance
from app.services.dg.database import offline_lookup, search_un_numbers
from app.services.dg.enrichment import segregation_groups_for

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg"


def product(un: str, **overrides):
    entry = offline_lookup(un) or {}
    base = {
        "un_number": un,
        "proper_shipping_name": entry.get("proper_shipping_name"),
        "class": entry.get("class"),
        "subsidiary_risks": entry.get("subsidiary_risks"),
        "packing_group": entry.get("packing_group"),
        "quantity_packages": "1",
    }
    return {**base, **overrides}


def imdg(*uns, language="nl"):
    entries = [{"line_id": 1, "products": [product(un) for un in uns]}]
    return check_compliance(entries, ["IMDG"], language)


# --- De laag zelf ------------------------------------------------------------

def test_the_amendment_layer_names_its_edition_and_source():
    assert amendment_42_24.amendment() == "42-24"
    assert "Hazcheck" in amendment_42_24.source()


def test_the_class_tables_are_confirmed_unchanged_in_42_24():
    """De bron noemt voor hoofdstuk 7.2 één wijziging: 7.2.6.1. De tabellen
    waar deze app op rekent staan er niet bij en gelden dus onverkort."""
    sections = amendment_42_24.verified_unchanged_sections()
    assert {"7.2.4", "7.2.6.3", "7.2.7.1.4", "3.1.4.4"} <= set(sections)
    amended = {item["section"] for item in amendment_42_24.amended_sections()}
    assert "7.2.6.1" in amended
    assert not amended & set(sections)


def test_the_layer_says_what_it_does_not_cover():
    assert amendment_42_24.not_covered("nl")
    assert amendment_42_24.not_covered("en")


# --- Nieuwe UN-nummers -------------------------------------------------------

def test_the_new_42_24_un_numbers_are_findable():
    """Natrium-ionbatterijen staan al in IMDG 42-24 en nog niet in ADR 2025.
    Wie ze over zee verscheept moet ze kunnen opzoeken."""
    hits = {r["un"] for r in search_un_numbers("sodium ion", 10)}
    assert {"3551", "3552", "3558"} <= hits


def test_a_new_un_number_carries_its_ems_and_says_where_it_comes_from():
    entry = offline_lookup("3553")
    assert entry["proper_shipping_name"] == "DISILANE"
    assert entry["class"] == "2.1"
    assert entry["ems_code"] == "F-D, S-U"
    assert "42-24" in entry["source"]


def test_every_new_un_number_has_a_class_and_an_ems_schedule():
    ems = amendment_42_24.ems_additions()
    for item in amendment_42_24.new_un_numbers():
        assert item.get("class"), item["un"]
        assert item["un"] in ems, item["un"]
        assert ems[item["un"]]["fire"].startswith("F-")
        assert ems[item["un"]]["spillage"].startswith("S-")


def test_the_new_entries_never_shadow_an_existing_adr_entry():
    seeded = {e["un"] for e in json.loads((SEED / "un_numbers.json").read_text("utf-8"))}
    assert not seeded & {i["un"] for i in amendment_42_24.new_un_numbers()}


# --- Gewijzigde stoffen ------------------------------------------------------

def test_isopropenylbenzene_became_a_marine_pollutant():
    """UN 2303 krijgt in 42-24 een 'P' in kolom 4 en SW1 erbij."""
    entry = offline_lookup("2303")
    assert entry["marine_pollutant_status"] == "yes"
    assert "SW1" in entry["imdg_stowage_codes"]
    assert entry["environmentally_hazardous"] is True


def test_carbon_keeps_its_old_stowage_code_and_gains_the_new_one():
    """Toevoegen, niet vervangen: SW1 stond er al, SW27 komt erbij."""
    codes = offline_lookup("1361")["imdg_stowage_codes"]
    assert codes == ["SW1", "SW27"]


def test_carbon_carries_the_new_document_requirement():
    requirement = offline_lookup("1361")["imdg_document_requirement"]
    assert requirement["section"] == "5.4.1.5.18"
    assert "productiedatum" in requirement["text"]
    assert "ambient_temperature_c" in requirement["fields"]


def test_a_reclassified_substance_is_reported_and_not_silently_rewritten():
    """UN 3423 wordt in 42-24 klasse 6.1 met nevengevaar 8. De app rekent de
    scheiding nog op de ADR-classificatie door en zegt dat er hardop bij; zij
    verandert de klasse niet achter de schermen."""
    entry = offline_lookup("3423")
    assert entry["class"] == "8"  # ADR 2025 ongewijzigd
    assert any("6.1" in line for line in entry["imdg_amendment_changes"])

    findings = imdg("3423")["imdg_segregation"]
    classification = [f for f in findings if "classificatie" in f["rule"]]
    assert len(classification) == 1
    assert classification[0]["severity"] == "warning"


def test_changes_are_reported_per_packing_group_where_they_differ():
    """UN 1835 verandert per verpakkingsgroep: alleen groep II krijgt 6.1."""
    two = amendment_42_24.changes_for("1835", "II", "nl")
    three = amendment_42_24.changes_for("1835", "III", "nl")
    assert any("6.1" in line for line in two)
    assert not any("6.1" in line for line in three)
    # Zonder verpakkingsgroep nooit de striktere variant.
    assert not any("6.1" in line for line in amendment_42_24.changes_for("1835", "", "nl"))


def test_the_changes_are_available_in_english():
    assert amendment_42_24.changes_for("2303", "", "en") != amendment_42_24.changes_for("2303", "", "nl")
    assert any("marine pollutant" in line for line in amendment_42_24.changes_for("2303", "", "en"))


def test_an_unaffected_substance_gets_no_amendment_noise():
    assert amendment_42_24.changes_for("1203") == []
    assert "imdg_amendment_changes" not in offline_lookup("1203")


# --- 7.2.3.1: kolom 16b gaat voor --------------------------------------------

def test_column_16b_takes_precedence_over_the_class_table():
    """Salpeterzuur × zwavel: de tabel zegt 'away from' (1), maar SG16 van
    salpeterzuur zegt 'separated from' (2). 7.2.3.1 laat er geen twijfel over
    bestaan welke van de twee geldt."""
    findings = imdg("2031", "1350")["imdg_segregation"]
    table = next(f for f in findings if f["rule"].startswith("IMDG 7.2.4"))
    sg16 = next(f for f in findings if "SG16" in f["rule"])

    assert table["superseded_by"] == [sg16["rule"]] or sg16["rule"] in table["superseded_by"]
    assert "7.2.3.1" in table["message"]
    assert table["severity"] == "info"
    assert "7.2.3.1" in sg16["message"]
    assert table["rule"] in sg16["takes_precedence_over"]


def test_the_superseded_finding_is_annotated_and_never_removed():
    findings = imdg("2031", "1350")["imdg_segregation"]
    assert any(f["rule"].startswith("IMDG 7.2.4") for f in findings)


def test_without_a_conflicting_16b_provision_the_table_stands():
    """Zoutzuur draagt geen SG16; dan blijft de tabelwaarde gewoon gelden."""
    findings = imdg("1789", "1350")["imdg_segregation"]
    table = next(f for f in findings if f["rule"].startswith("IMDG 7.2.4"))
    assert "superseded_by" not in table
    assert table["severity"] == "warning"


def test_agreement_between_the_two_is_not_reported_as_a_conflict():
    findings = apply_column_16b_precedence([
        {"rule": "IMDG 7.2.4 (8 × 4.1)", "severity": "warning", "code": "2",
         "message": "x", "products": "A  ×  B", "source": "table", "pair": "A|B"},
        {"rule": "IMDG 16b (SG16)", "severity": "warning", "code": "2",
         "message": "y", "products": "A  ×  B", "source": "column_16b", "pair": "A|B"},
    ], "nl")
    assert "superseded_by" not in findings[0]
    assert findings[0]["message"] == "x"


def test_all_provisions_at_the_strictest_level_carry_the_precedence():
    """Twee SG-codes van gelijke zwaarte op hetzelfde paar: allebei gaan ze
    voor, dus allebei krijgen ze de vermelding."""
    findings = apply_column_16b_precedence([
        {"rule": "IMDG 7.2.4 (8 × 4.1)", "severity": "warning", "code": "1",
         "message": "x", "products": "A  ×  B", "source": "table", "pair": "A|B"},
        {"rule": "IMDG 16b (SG16)", "severity": "warning", "code": "2",
         "message": "y", "products": "A  ×  B", "source": "column_16b", "pair": "A|B"},
        {"rule": "IMDG 16b (SG17)", "severity": "warning", "code": "2",
         "message": "z", "products": "B  ×  A", "source": "column_16b", "pair": "A|B"},
    ], "nl")
    assert all("7.2.3.1" in f["message"] for f in findings[1:])
    assert set(findings[0]["superseded_by"]) == {"IMDG 16b (SG16)", "IMDG 16b (SG17)"}


def test_a_stricter_16b_provision_raises_the_severity_to_error():
    findings = apply_column_16b_precedence([
        {"rule": "IMDG 7.2.4 (3 × 5.1)", "severity": "warning", "code": "1",
         "message": "x", "products": "A  ×  B", "source": "table", "pair": "A|B"},
        {"rule": "IMDG 16b (SG9)", "severity": "warning", "code": "4",
         "message": "y", "products": "A  ×  B", "source": "column_16b", "pair": "A|B"},
    ], "nl")
    assert findings[1]["severity"] == "error"
    assert findings[0]["severity"] == "info"


# --- SGG1a bestaat niet meer -------------------------------------------------

def test_sgg1a_is_gone_from_the_segregation_groups():
    """De aparte markering voor sterke zuren verviel met 41-22 en 42-24 laat
    3.1.4.4 ongewijzigd. Zij mag nergens meer opduiken."""
    seed = json.loads((SEED / "segregation_groups.json").read_text("utf-8"))
    assert not any("SGG1a" in codes for codes in seed["by_un"].values())
    assert all(group.get("alt_code") is None for group in seed["groups"])
    assert segregation_groups_for("1789") == ["SGG1"]


def test_the_group_counts_match_the_entries():
    seed = json.loads((SEED / "segregation_groups.json").read_text("utf-8"))
    for group in seed["groups"]:
        actual = sum(1 for codes in seed["by_un"].values() if group["code"] in codes)
        assert group["count"] == actual, group["code"]


# --- Wat elke uitkomst over zijn eigen edities zegt --------------------------

def test_every_result_names_the_editions_it_used():
    rule_sets = imdg("1203")["rule_sets"]
    assert "42-24" in rule_sets["IMDG_current_mandatory"]
    assert "NIET geladen" not in rule_sets["IMDG_current_mandatory"]
    assert "7.2.4" in rule_sets["IMDG_class_tables"]
    assert rule_sets["IMDG_42_24_not_covered"]
    assert "Hazcheck" in rule_sets["IMDG_42_24_source"]


@pytest.mark.parametrize("language", ["nl", "en"])
def test_the_edition_metadata_survives_both_languages(language):
    rule_sets = imdg("1203", language=language)["rule_sets"]
    assert rule_sets["IMDG_42_24_not_covered"]


# --- De codetabel uit hoofdstuk 7.1.5, 7.1.6 en 7.2.8 ------------------------

def test_the_code_table_is_complete():
    """SW1-SW31, H1-H5 en SG1-SG78. De enige echte gaten zijn SG64, SG66 en
    SG73 (gereserveerd) en SG75, dat met 41-22 verviel — net als SGG1a."""
    table = json.loads((SEED / "imdg_codes.json").read_text("utf-8"))
    assert table["amendment"] == "42-24"

    stowage = table["stowage_codes"]["codes"]
    assert len(stowage) == 31 and "SW31" in stowage

    assert len(table["handling_codes"]["codes"]) == 5

    segregation = table["segregation_codes"]
    assert table["segregation_codes"]["reserved"] == ["SG64", "SG66", "SG73"]
    numbers = {int(c[2:]) for c in segregation["codes"]}
    assert 75 not in numbers
    assert set(range(1, 79)) - numbers - {64, 66, 73} == {75}


def test_a_reserved_code_carries_no_guidance():
    from app.services.dg.enrichment import imdg_code_text
    assert imdg_code_text("SG64") == ""
    assert imdg_code_text("SG65").startswith("Stow")


def test_the_official_wording_reaches_the_substance():
    """Salpeterzuur draagt SG16; de gebruiker moet lezen wat dat betekent."""
    definitions = offline_lookup("2031")["imdg_segregation_definitions"]
    by_code = {d["code"]: d["text"] for d in definitions}
    assert by_code["SG16"] == "Stow “separated from” class 4.1."


def test_the_official_wording_beats_the_card_paraphrase():
    """7.2.8 is de bron; de zin van de UN-kaart is een parafrase en wijkt."""
    from app.services.dg.compliance import _wording
    from app.services.dg.enrichment import segregation_provisions
    rules = segregation_provisions()
    assert _wording("SG16", rules) == "Stow “separated from” class 4.1."
    assert _wording("SG16", rules) != rules.get("SG16", {}).get("text")


def test_an_unknown_code_falls_back_instead_of_going_blank():
    from app.services.dg.compliance import _wording
    assert _wording("SG999", {"SG999": {"text": "from the card"}}) == "from the card"
    assert _wording("SG999", {}) == ""
