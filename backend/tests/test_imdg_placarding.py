"""What a container going to sea has to show on the outside (IMDG 5.3).

Road, rail and inland waterway have had chapter 5.3 derived for several
releases; sea had nothing, on the belief that the Code was unavailable. It is
not — resolution MSC.556(108) replaces the complete text — and reading it
showed that the sea chapter differs from the land ones in ways that would each
have produced a wrong answer if the road rule had been reused:

* four sides, not two, and not "only for class 1 and 7";
* the UN number inside the placard or on an orange panel beside it, in five
  named cases only, and never for class 1;
* the proper shipping name marked on the unit itself;
* the marine pollutant mark, which no land regime has;
* class 9 placarded as model No. 9 — while table A gives 9A for exactly the
  battery entries most likely to travel in a container.

These tests pin those five, plus the two thresholds the chapter states as
numbers, because a number read once is a number that can drift.
"""
import pytest

from app.core.languages import SUPPORTED
from app.services.dg.compliance import check_imdg_placarding


def placard_for(*products, language: str = "nl") -> dict:
    return check_imdg_placarding([{"products": list(products)}], language)


def provisions(result: dict) -> list[str]:
    return [item["provision"] for item in result["placards"]]


def mark_kinds(result: dict) -> list[str]:
    return [item["kind"] for item in result["marks"]]


def message_for(result: dict, provision: str, key: str = "placards") -> str:
    return next(item["message"] for item in result[key]
                if item["provision"] == provision)


# --- the placards ------------------------------------------------------------


def test_an_empty_consignment_is_not_checked():
    assert check_imdg_placarding([], "nl")["status"] == "not_checked"


def test_the_placard_follows_the_primary_hazard():
    result = placard_for({"un_number": "1203", "class": "3",
                          "proper_shipping_name": "GASOLINE"})
    assert result["status"] == "ok"
    assert result["placards"][0]["label_models"] == ["3"]
    assert result["placards_required"] is True


def test_class_nine_is_placarded_as_nine_never_as_nine_a():
    """5.3.1.1.2: "label model No. 9A shall not be used for placarding
    purposes." Table A gives 9A for the lithium and sodium battery entries, so
    carrying the label model across unchanged puts the wrong placard on a
    container of batteries — which is what a shipper would then order."""
    result = placard_for({"un_number": "3480", "class": "9", "labels": "9A",
                          "proper_shipping_name": "LITHIUM ION BATTERIES"})
    models = result["placards"][0]["label_models"]
    assert models == ["9"]
    assert "9A" not in models


def test_division_one_four_s_needs_no_placard_at_any_quantity():
    """5.3.1.1.2.1 — and "any quantity" is the point: there is no threshold
    below which this changes, and none above it either."""
    result = placard_for({"un_number": "0012", "class": "1.4",
                          "classification_code": "1.4S",
                          "proper_shipping_name": "CARTRIDGES FOR WEAPONS"})
    assert "5.3.1.1.2.1" in provisions(result)
    assert result["placards_required"] is False
    # And it is not silently given a class 1 placard on the way past.
    assert not any(item.get("label_models") for item in result["placards"])


def test_several_class_one_divisions_show_only_the_highest():
    result = placard_for(
        {"un_number": "0004", "class": "1.1", "classification_code": "1.1D"},
        {"un_number": "0027", "class": "1.3", "classification_code": "1.3C"})
    assert "5.3.1.1.2.2" in provisions(result)
    assert result["placards"][0]["label_models"] == ["1.1"]


def test_subsidiary_hazards_get_their_own_placards():
    result = placard_for({"un_number": "1092", "class": "6.1",
                          "subsidiary_risks": "3",
                          "proper_shipping_name": "ACROLEIN, STABILIZED"})
    assert "5.3.1.1.3" in provisions(result)
    assert "3" in message_for(result, "5.3.1.1.3")


def test_every_kind_of_unit_gets_its_own_placement_rule():
    """The application cannot see which kind of unit the goods travel in, and
    the kind decides the placement — so all five are given rather than one
    standing in for the rest."""
    result = placard_for({"un_number": "1203", "class": "3"})
    for provision in ("5.3.1.1.4.1.1", "5.3.1.1.4.1.2", "5.3.1.1.4.1.3",
                      "5.3.1.1.4.1.4", "5.3.1.1.4.1.5"):
        assert provision in provisions(result)


def test_a_container_is_placarded_on_all_four_sides():
    """The difference from the road that costs the most if reused: a freight
    container carries a placard on each side *and each end*."""
    result = placard_for({"un_number": "1203", "class": "3"}, language="en")
    text = message_for(result, "5.3.1.1.4.1.1")
    assert "each side" in text and "each end" in text


def test_class_seven_gets_the_seven_d_placard():
    result = placard_for({"un_number": "2912", "class": "7",
                          "proper_shipping_name": "RADIOACTIVE MATERIAL, LSA-I"})
    assert "5.3.1.1.5.1" in provisions(result)
    assert "7D" in message_for(result, "5.3.1.1.5.1")


# --- the marking half --------------------------------------------------------


def test_the_proper_shipping_name_is_marked_on_the_unit():
    """5.3.2.0.1 has no land counterpart at all."""
    result = placard_for({"un_number": "1203", "class": "3"})
    assert "proper_shipping_name" in mark_kinds(result)


def test_a_marine_pollutant_carries_the_mark_no_land_regime_has():
    result = placard_for({"un_number": "3082", "class": "9",
                          "marine_pollutant": "P",
                          "proper_shipping_name":
                          "ENVIRONMENTALLY HAZARDOUS SUBSTANCE, LIQUID, N.O.S."})
    assert "marine_pollutant" in mark_kinds(result)


def test_goods_that_are_not_marine_pollutants_get_no_mark():
    result = placard_for({"un_number": "1203", "class": "3"})
    assert "marine_pollutant" not in mark_kinds(result)


def test_a_tank_shows_the_un_number_and_class_one_never_does():
    tank = placard_for({"un_number": "1203", "class": "3",
                        "carriage_mode": "portable_tank"})
    assert "5.3.2.1.1.1" in [m["provision"] for m in tank["marks"]]

    explosives = placard_for({"un_number": "0004", "class": "1.1",
                              "classification_code": "1.1D"})
    assert "5.3.2.1.1" in [m["provision"] for m in explosives["marks"]]


def test_four_tonnes_of_one_substance_brings_the_un_number_onto_the_unit():
    """5.3.2.1.1.2, the one arithmetic condition in the chapter: more than
    4,000 kg gross of a single UN number that is the only dangerous goods."""
    heavy = placard_for({"un_number": "1203", "class": "3",
                         "gross_mass_per_package": "250 kg",
                         "quantity_packages": "20"})  # 5,000 kg
    required = next(m for m in heavy["marks"]
                    if m["provision"] == "5.3.2.1.1.2")
    assert required["required"] is True

    light = placard_for({"un_number": "1203", "class": "3",
                         "gross_mass_per_package": "20 kg",
                         "quantity_packages": "10"})  # 200 kg
    assert not any(m["provision"] == "5.3.2.1.1.2" and m.get("required") is True
                   for m in light["marks"])


def test_an_unknown_mass_is_reported_as_unassessed_rather_than_as_under_the_limit():
    """The failure mode this guards against is the quiet one: a missing mass
    silently reading as "not over 4,000 kg" and the mark never being named."""
    result = placard_for({"un_number": "1203", "class": "3"})
    unassessed = next(m for m in result["marks"]
                      if m["provision"] == "5.3.2.1.1.2")
    assert unassessed["required"] is None


def test_a_hot_load_brings_the_elevated_temperature_mark():
    """5.3.2.2.1: liquid at 100 °C or above. The carriage temperature is a
    field precisely because nothing else in the consignment implies it."""
    result = placard_for({"un_number": "2448", "class": "4.1",
                          "carriage_temperature": "130",
                          "proper_shipping_name": "SULPHUR, MOLTEN"})
    mark = next(m for m in result["marks"]
                if m["kind"] == "elevated_temperature")
    assert mark["required"] is True
    assert "130" in mark["message"]


def test_a_warm_load_below_the_threshold_gets_no_mark():
    result = placard_for({"un_number": "1203", "class": "3",
                          "carriage_temperature": "40"})
    assert "elevated_temperature" not in mark_kinds(result)


def test_molten_without_a_temperature_says_so_instead_of_staying_silent():
    """MOLTEN says the substance travels liquid, not how hot. Answering "no
    mark required" from that would be an invention; saying the temperature is
    missing is the honest answer."""
    result = placard_for({"un_number": "2448", "class": "4.1", "molten": "yes",
                          "proper_shipping_name": "SULPHUR, MOLTEN"})
    mark = next(m for m in result["marks"]
                if m["kind"] == "elevated_temperature")
    assert mark["required"] is None


def test_the_unit_is_stripped_after_discharge_and_survives_the_sea():
    result = placard_for({"un_number": "1203", "class": "3"})
    assert "removal" in mark_kinds(result)
    assert "seawater" in mark_kinds(result)


# --- the four languages ------------------------------------------------------


@pytest.mark.parametrize("language", SUPPORTED)
def test_every_finding_speaks_the_document_language(language):
    result = placard_for(
        {"un_number": "3082", "class": "9", "marine_pollutant": "P",
         "carriage_temperature": "120"},
        language=language)
    for item in result["placards"] + result["marks"]:
        assert item["message"].strip()


def test_the_source_names_the_chapter_it_was_read_from():
    result = placard_for({"un_number": "1203", "class": "3"})
    assert "MSC.556(108)" in result["source"]
    assert "5.3" in result["source"]
