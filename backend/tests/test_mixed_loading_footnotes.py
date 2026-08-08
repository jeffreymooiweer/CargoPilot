"""De lege vakjes van tabel 7.5.2.1 zijn niet allemaal leeg.

Uit de praktijk gemeld: springstof samen met ammoniumnitraat werd geweigerd,
terwijl voetnoot (d) het uitdrukkelijk toestaat. De melding die de applicatie
gaf noemde die uitzondering zelfs bij naam — en weigerde vervolgens toch. Dat is
de vervelendste soort fout: het scherm bewijst dat de regel bekend was en dat er
niets mee gedaan is.

De oorzaak was de vorm van de controle. Ze keek of er ergens in de zending een
collo van klasse 1 zat en ergens een collo van een andere klasse, en gaf dan één
foutmelding over de hele zending. Tabel 7.5.2.1 werkt niet zo: die zet etiket
tegen etiket, vakje voor vakje, en in drie van die vakjes staat een letter in
plaats van niets.

De tekst is nagelezen in ADR 2025 Volume II (ECE/TRANS/352 Vol. II), tabel
7.5.2.1, gedrukte bladzijde 592. Voetnoot (d) luidt daar:

    "Mixed loading permitted between blasting explosives (except UN No. 0083
     explosive, blasting, type C) and ammonium nitrate (UN Nos. 1942 and 2067),
     ammonium nitrate emulsion or suspension or gel (UN No. 3375) and alkali
     metal nitrates and alkaline earth metal nitrates provided the aggregate is
     treated as blasting explosives under Class 1 for the purposes of
     placarding, segregation, stowage and maximum permissible load."

Die laatste voorwaarde is geen bijzin. Wie zich op (d) beroept, verlegt de
placardering en de maximaal toegestane hoeveelheid van 7.5.5.2.1 naar klasse 1.
Toestaan zonder dat erbij te zeggen zou de vergissing alleen maar omdraaien.
"""

import pytest

from app.services.dg.compliance import check_adr_mixed_loading

# UN 0081 explosive, blasting, type A — een springstof zoals voetnoot (d) bedoelt.
BLASTING = {"un_number": "0081", "class": "1.1D",
            "proper_shipping_name": "EXPLOSIVE, BLASTING, TYPE A"}
# UN 0083 is met zoveel woorden uitgezonderd.
TYPE_C = {"un_number": "0083", "class": "1.1D",
          "proper_shipping_name": "EXPLOSIVE, BLASTING, TYPE C"}
AMMONIUM_NITRATE = {"un_number": "1942", "class": "5.1",
                    "proper_shipping_name": "AMMONIUM NITRATE"}
PAINT = {"un_number": "1263", "class": "3", "proper_shipping_name": "PAINT"}


def load(*products, language="en"):
    entries = [{"line_id": "L1", "products": list(products)}]
    return check_adr_mixed_loading(entries, language)


def by_rule(warnings, prefix):
    return [w for w in warnings if w["rule"].startswith(prefix)]


def errors(warnings):
    return [w for w in warnings if w["severity"] == "error"]


# --- De melding zelf ------------------------------------------------------


def test_blasting_explosives_with_ammonium_nitrate_are_no_longer_refused():
    assert errors(load(BLASTING, AMMONIUM_NITRATE)) == []


def test_the_footnote_that_permits_it_is_named():
    [warning] = by_rule(load(BLASTING, AMMONIUM_NITRATE), "ADR 7.5.2.1")
    assert warning["rule"] == "ADR 7.5.2.1 (d)"
    assert warning["severity"] == "warning"


def test_the_condition_travels_with_the_permission():
    """Toestaan zonder de voorwaarde is een tweede fout, geen oplossing."""
    [warning] = by_rule(load(BLASTING, AMMONIUM_NITRATE), "ADR 7.5.2.1")
    message = warning["message"].lower()
    assert "placarding" in message
    assert "maximum permissible load" in message
    assert "7.5.5.2.1" in warning["message"]


def test_both_packages_are_named_in_the_outcome():
    [warning] = by_rule(load(BLASTING, AMMONIUM_NITRATE), "ADR 7.5.2.1")
    assert "0081" in warning["products"] and "1942" in warning["products"]


# --- De grenzen van voetnoot (d) ------------------------------------------


def test_type_c_is_excluded_by_the_footnote_itself():
    """"(except UN No. 0083 explosive, blasting, type C)" — dat is de hele
    reden dat het nummer apart in de configuratie staat."""
    assert errors(load(TYPE_C, AMMONIUM_NITRATE))


def test_an_explosive_that_is_not_a_blasting_explosive_stays_refused():
    """UN 0336 is vuurwerk. Voetnoot (d) gaat over springstof."""
    fireworks = {"un_number": "0336", "class": "1.4G"}
    assert errors(load(fireworks, AMMONIUM_NITRATE))


def test_a_class_5_1_substance_outside_the_list_stays_refused():
    """Niet elk oxiderend goed is een nitraat dat de voetnoot noemt."""
    peroxide = {"un_number": "2014", "class": "5.1"}
    assert errors(load(BLASTING, peroxide))


@pytest.mark.parametrize("un,what", [
    ("2067", "ammonium nitrate based fertilizer"),
    ("3375", "ammonium nitrate emulsion"),
    ("1498", "sodium nitrate, an alkali metal nitrate"),
    ("1486", "potassium nitrate, an alkali metal nitrate"),
    ("1454", "calcium nitrate, an alkaline earth metal nitrate"),
    ("1507", "strontium nitrate, an alkaline earth metal nitrate"),
])
def test_every_nitrate_the_footnote_names_is_covered(un, what):
    """De voetnoot somt de nitraten met nummer en al op; ze overslaan zou de
    helft van de bepaling weglaten."""
    assert errors(load(BLASTING, {"un_number": un, "class": "5.1"})) == [], what


# --- Per paar, niet per zending -------------------------------------------


def test_a_permitted_pair_does_not_excuse_a_forbidden_one():
    """Springstof mag bij het nitraat, maar niet bij de verf. Als de controle
    over de hele zending oordeelt, verdwijnt precies dat onderscheid."""
    warnings = load(BLASTING, AMMONIUM_NITRATE, PAINT)
    [error] = errors(warnings)
    assert "1263" in error["products"]
    assert "1942" not in error["products"]


def test_and_the_permission_survives_alongside_the_refusal():
    warnings = load(BLASTING, AMMONIUM_NITRATE, PAINT)
    assert by_rule(warnings, "ADR 7.5.2.1 (d)")


def test_the_ordinary_prohibition_is_untouched():
    error = errors(load(BLASTING, PAINT))
    assert len(error) == 1
    assert error[0]["rule"] == "ADR 7.5.2.1"


# --- De andere twee voetnoten ---------------------------------------------


def test_life_saving_appliances_are_permitted_under_b():
    """UN 2990 is een reddingsmiddel van klasse 9."""
    warnings = load(BLASTING, {"un_number": "2990", "class": "9"})
    assert errors(warnings) == []
    assert by_rule(warnings, "ADR 7.5.2.1 (b)")


def test_a_class_9_that_is_not_a_life_saving_appliance_stays_refused():
    assert errors(load(BLASTING, {"un_number": "3082", "class": "9"}))


def test_the_safety_device_pair_is_permitted_under_c():
    """UN 0503 met UN 3268 — pyrotechnisch en elektrisch geactiveerd."""
    warnings = load({"un_number": "0503", "class": "1.4G"},
                    {"un_number": "3268", "class": "9"})
    assert errors(warnings) == []
    assert by_rule(warnings, "ADR 7.5.2.1 (c)")


def test_one_four_s_is_still_no_obstacle_at_all():
    """Voetnoot (a) staat 1.4S overal toe; dat liep al goed en moet zo blijven."""
    assert load({"un_number": "0012", "class": "1.4S"}, PAINT) == []


# --- Wat er verder niet mag veranderen ------------------------------------


def test_a_shipment_without_class_one_says_nothing_about_7_5_2_1():
    assert by_rule(load(PAINT, AMMONIUM_NITRATE), "ADR 7.5.2.1") == []


@pytest.mark.parametrize("language", ["nl", "en", "de"])
def test_the_footnote_speaks_every_interface_language(language):
    [warning] = by_rule(load(BLASTING, AMMONIUM_NITRATE, language=language), "ADR 7.5.2.1")
    assert "7.5.5.2.1" in warning["message"]
    assert len(warning["message"]) > 80


def test_the_condition_reaches_the_document_and_not_only_the_screen():
    """De voorwaarde van (d) verlegt de placardering en de maximaal toegestane
    hoeveelheid. Dat overleeft de sessie niet als het alleen op het scherm staat.
    """
    from app.services.documents.exporter import get_document, validate_document

    line = [{"line_id": "L1", "products": [
        dict(BLASTING, quantity_packages="1", type_of_package="box"),
        dict(AMMONIUM_NITRATE, quantity_packages="1", type_of_package="box"),
    ]}]
    errors_out, warnings_out = validate_document(get_document("cmr"), {}, [], line, "en")
    assert any("7.5.2.1 (d)" in warning for warning in warnings_out)
    assert not any("7.5.2.1:" in error for error in errors_out)


def test_the_source_of_the_numbers_is_recorded():
    """Deze nummers komen uit een tekst die niet in de repository staat. Waar
    ze vandaan komen hoort er dan wel in te staan."""
    from app.services.dg.compliance import get_compliance_rules

    source = get_compliance_rules()["adr_mixed_loading"]["_footnotes_source"]
    assert "7.5.2.1" in source and "ECE/TRANS/352" in source


def test_the_rail_check_is_recorded_too():
    """Een verbod lenen van een ander regime is voorzichtig; een toestemming
    lenen is dat niet. Deze voetnoten gelden ook voor het spoor omdat RID ze
    woordelijk zo heeft — nagekeken, niet aangenomen."""
    from app.services.dg.compliance import get_compliance_rules

    rail = get_compliance_rules()["adr_mixed_loading"]["_footnotes_rail"]
    assert "RID 2025" in rail and "7.5.2.1" in rail


def test_rail_gets_the_same_answer_as_road():
    from app.services.dg.compliance import check_compliance

    entries = [{"line_id": "L1", "products": [BLASTING, AMMONIUM_NITRATE]}]
    for profile in ("ADR", "RID"):
        out = check_compliance(entries, [profile], "en")["adr_mixed_loading"]
        assert [w["rule"] for w in out if w["rule"].startswith("ADR 7.5.2.1")] \
            == ["ADR 7.5.2.1 (d)"], profile
