"""Tests for automatic completion and per-mode enrichment of DG data."""

import json
import re
from pathlib import Path

from app.services.dg.autofill import adr_category_totals, description_line, prepare_entries
from app.services.dg.compliance import (
    check_imdg_class1_compatibility,
    check_imdg_segregation,
    check_imdg_segregation_groups,
    get_compliance_rules,
)
from app.services.dg.database import is_transport_forbidden
from app.services.dg.enrichment import (
    describe_ems,
    describe_excepted_quantity,
    enrich_un_entry,
    lookup_ems,
    parse_hazards,
    segregation_groups_for,
)
from app.services.documents.exporter import validate_document
from app.services.documents.registry import get_document


def test_parse_hazards_separates_classification_code_from_subsidiary_risks():
    """The classification code (F1) is not a subsidiary risk — the labels were."""
    petrol = parse_hazards({"class": "3", "classification_code": "F1", "labels": "3"})
    assert petrol["division"] == "3"
    assert petrol["subsidiary_risks"] == []
    assert petrol["classification_code"] == "F1"

    nitric = parse_hazards({"class": "8", "classification_code": "CO1", "labels": "8+5.1"})
    assert nitric["division"] == "8"
    assert nitric["subsidiary_risks"] == ["5.1"]


def test_parse_hazards_resolves_division_for_gases_and_explosives():
    """Table A gives only '2' for gases and only '1' for explosives."""
    lpg = parse_hazards({"class": "2", "classification_code": "2F", "labels": "2.1"})
    assert lpg["division"] == "2.1"

    fireworks = parse_hazards({"class": "1", "classification_code": "1.4G", "labels": "1.4"})
    assert fireworks["division"] == "1.4G"

    lithium = parse_hazards({"class": "9", "classification_code": "M4", "labels": "9A"})
    assert lithium["division"] == "9"
    assert lithium["subsidiary_risks"] == []


def test_enrichment_provides_ems_and_air_rules():
    petrol = enrich_un_entry({"un": "1203", "class": "3", "excepted_quantity": "E2", "limited_quantity": "1 L"})
    assert petrol["ems_code"] == "F-E, S-E"
    assert petrol["ems_source"] == "ems_guide"
    assert "drijven" in petrol["ems_description"]
    assert "30 g/ml" in petrol["excepted_quantity_text"]

    lithium = enrich_un_entry({"un": "3480", "class": "9", "excepted_quantity": "E0"})
    assert lithium["cargo_aircraft_only"] is True
    assert lithium["iata_packing_instruction"] == "965"

    toxic_gas = enrich_un_entry({"un": "1017", "class": "2", "labels": "2.3+5.1+8"})
    assert toxic_gas["air_forbidden"] is True


def test_ems_seed_matches_the_official_guide_structure():
    """Index of MSC.1/Circ.1588/Rev.3: 10 fire and 26 spillage schedules."""
    seed = json.loads(
        (Path(__file__).resolve().parents[1] / "seed" / "dg" / "ems.json").read_text(encoding="utf-8")
    )
    fire, spill, entries = seed["fire_schedules"], seed["spillage_schedules"], seed["entries"]
    assert sorted(fire) == [f"F-{c}" for c in "ABCDEFGHIJ"]
    assert sorted(spill) == [f"S-{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
    assert len(entries) >= 2300

    for un, item in entries.items():
        assert re.fullmatch(r"\d{4}", un), un
        options = [item] if "fire" in item else (
            item.get("variants") or list(item.get("by_packing_group", {}).values())
        )
        assert options, f"{un}: geen schema"
        for option in options:
            assert option["fire"] in fire, f"{un}: {option['fire']}"
            assert option["spillage"] in spill, f"{un}: {option['spillage']}"


def test_ems_lookup_matches_the_official_index():
    """A sample, taken verbatim from the index of the EmS Guide."""
    expected = {
        "1203": ("F-E", "S-E"),  # benzine
        "1170": ("F-E", "S-D"),  # ethanol
        "1230": ("F-E", "S-D"),  # methanol
        "1219": ("F-E", "S-D"),  # isopropanol
        "1114": ("F-E", "S-D"),  # benzeen
        "1993": ("F-E", "S-E"),  # brandbare vloeistof n.e.g.
        "1789": ("F-A", "S-B"),  # zoutzuur
        "1950": ("F-D", "S-U"),  # spuitbussen
        "3480": ("F-A", "S-I"),  # lithium-ionbatterijen
    }
    for un, (fire, spillage) in expected.items():
        item = lookup_ems(un)
        assert item is not None, f"UN {un} ontbreekt"
        assert (item["fire"], item["spillage"]) == (fire, spillage), un


def test_ems_handles_packing_group_and_variant_entries():
    """A few entries have their own schedule per packing group or variant."""
    # UN 1826, nitreerzuurmengsel: PG I oxiderend (S-Q), PG II bijtend (S-B).
    pg1 = lookup_ems("1826", "I")
    pg2 = lookup_ems("1826", "II")
    assert (pg1["fire"], pg1["spillage"]) == ("F-A", "S-Q")
    assert (pg2["fire"], pg2["spillage"]) == ("F-A", "S-B")
    # Without a packing group the choices are returned instead of a guess.
    assert "packing_group_options" in lookup_ems("1826")

    # UN 3166: gas- and liquid-powered vehicles each have their own schedule.
    variants = enrich_un_entry({"un": "3166", "class": "9"}, "nl")["ems_variants"]
    codes = {v["label"]: v["code"] for v in variants}
    assert codes == {"for gases": "F-D, S-U", "for liquids": "F-E, S-E"}


def test_ems_schedule_descriptions_are_available_in_both_languages():
    assert describe_ems("F-B", "nl").startswith("F-B (Explosieve stoffen")
    assert describe_ems("S-E", "en") == "S-E (Flammable liquids, floating on water)"
    assert describe_ems("F-E, S-D", "nl").count("·") == 1


def test_ems_falls_back_to_division_for_gases():
    """Table A gives only '2' for gases; the division comes from the labels."""
    flammable = enrich_un_entry({"un": "9998", "class": "2", "labels": "2.1"})
    assert flammable["ems_class_default"] == "F-D, S-U"
    inert = enrich_un_entry({"un": "9997", "class": "2", "labels": "2.2"})
    assert inert["ems_class_default"] == "F-C, S-V"
    assert flammable["ems_source"] == "class_default"


def test_transport_forbidden_substances_are_flagged_and_block_export():
    """ADR Table A marks 14 substances as not admitted for carriage."""
    forbidden = enrich_un_entry({"un": "1798", "class": "8", "labels": "BEFÖRDERUNG VERBOTEN"}, "nl")
    assert forbidden["transport_forbidden"] is True
    assert "niet ten vervoer" in forbidden["transport_forbidden_note"]

    assert is_transport_forbidden("1798") is True   # koningswater
    assert is_transport_forbidden("2249") is True   # symmetrisch dichloordimethylether
    assert is_transport_forbidden("1203") is False  # benzine

    document = get_document("avc_waybill")
    errors, _ = validate_document(
        document,
        {},
        [],
        [{"line_id": 1, "vehicle": "Vat", "products": [{
            "un_number": "1798",
            "proper_shipping_name": "NITROHYDROCHLORIC ACID",
            "class": "8",
        }]}],
        "nl",
    )
    assert any("Niet ten vervoer toegelaten" in e for e in errors)


def test_excepted_quantity_limits_match_adr_3_5_1_2():
    assert "30 g/ml per binnenverpakking" in describe_excepted_quantity("E1", "nl")
    assert "1000 g/ml per buitenverpakking" in describe_excepted_quantity("E1", "nl")
    assert "300 g/ml per outer packaging" in describe_excepted_quantity("E5", "en")
    assert describe_excepted_quantity("E0", "nl").startswith("E0: niet toegestaan")
    assert describe_excepted_quantity("", "nl") is None


def test_prepare_fills_classification_and_quantities_from_lines():
    entries = [{
        "line_id": 1,
        "vehicle": "Jerrycans",
        "products": [{"un_number": "1203", "net_mass_liters_per_package": "20 L"}],
    }]
    lines = [{"line_id": 1, "quantity": 10, "unit": "jerrycan", "weight_each_kg": 16.5}]

    result = prepare_entries(entries, lines, ["ADR"], "nl")
    product = result["entries"][0]["products"][0]

    assert product["proper_shipping_name"].startswith("GASOLINE")
    assert product["class"] == "3"
    assert product["packing_group"] == "II"
    assert product["transport_category"] == "2"
    assert product["tunnel_code"] == "D/E"
    assert product["quantity_packages"] == "10"
    assert product["type_of_package"] == "jerrycan"
    # 10 packages × 20 L = 200 L, automatically for the 1.1.3.6 points
    assert product["adr_total_quantity"] == "200 L"


def test_prepare_never_overwrites_manual_input():
    entries = [{
        "line_id": 1,
        "vehicle": "Handmatig",
        "products": [{
            "un_number": "1203",
            "proper_shipping_name": "BENZINE (eigen omschrijving)",
            "quantity_packages": "3",
        }],
    }]
    lines = [{"line_id": 1, "quantity": 99, "unit": "vat", "weight_each_kg": 1}]

    product = prepare_entries(entries, lines, ["ADR"], "nl")["entries"][0]["products"][0]
    assert product["proper_shipping_name"] == "BENZINE (eigen omschrijving)"
    assert product["quantity_packages"] == "3"


def test_description_line_follows_adr_5_4_1_1_1():
    product = {
        "un_number": "1203",
        "proper_shipping_name": "BENZINE",
        "class": "3",
        "packing_group": "II",
        "tunnel_code": "D/E",
        "quantity_packages": "10",
        "type_of_package": "jerrycan",
        "net_mass_liters_per_package": "20 L",
    }
    assert description_line(product, "ADR") == "UN 1203, BENZINE, 3, II, (D/E), 10 jerrycan, 200 L"


def test_description_line_adds_imdg_and_iata_specifics():
    product = {
        "un_number": "3480",
        "proper_shipping_name": "LITHIUM ION BATTERIES",
        "class": "9",
        "ems_code": "F-A, S-I",
        "marine_pollutant": "P",
        "cargo_aircraft_only": "Y",
        "iata_packing_instruction": "965",
        "quantity_packages": "2",
        "type_of_package": "doos",
        "net_mass_liters_per_package": "5 kg",
    }
    imdg = description_line(product, "IMDG")
    assert "MARINE POLLUTANT" in imdg and "EmS F-A, S-I" in imdg

    iata = description_line(product, "IATA_DGR")
    assert "PI 965" in iata and "CARGO AIRCRAFT ONLY" in iata
    # The ADR packing instruction does not belong on an air freight document.
    assert "P001" not in iata


def test_adr_category_totals_group_per_transport_category():
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            {"transport_category": "2", "quantity_packages": "10", "net_mass_liters_per_package": "20 L"},
            {"transport_category": "2", "quantity_packages": "2", "net_mass_liters_per_package": "5 L"},
            {"transport_category": "1", "quantity_packages": "4", "net_mass_liters_per_package": "25 kg"},
        ],
    }]
    totals = adr_category_totals(entries, "nl")
    rows = {row["transport_category"]: row["total"] for row in totals["categories"]}
    assert rows["2"] == "210 L"
    assert rows["1"] == "100 kg"
    assert "Totale hoeveelheid per vervoerscategorie" in totals["statement"]


def test_imdg_segregation_table_is_symmetric_and_complete():
    rules = get_compliance_rules()["imdg_segregation"]
    order = rules["class_order"]
    table = rules["table"]
    assert set(table) == set(order)
    for row in order:
        assert len(table[row]) == len(order)
        for index, column in enumerate(order):
            assert table[row][index] == table[column][order.index(row)], f"{row}×{column}"


def test_imdg_segregation_table_matches_amendment_40_20():
    """Taken verbatim from IMDG Code chapter 7.2, table 7.2.4 (Amdt 40-20)."""
    official = {
        "1.1-1.2-1.5": "* * * 4 2 2 4 4 4 4 4 4 2 4 2 4 X",
        "1.3-1.6":     "* * * 4 2 2 4 3 3 4 4 4 2 4 2 2 X",
        "1.4":         "* * * 2 1 1 2 2 2 2 2 2 X 4 2 2 X",
        "2.1":         "4 4 2 X X X 2 1 2 2 2 2 X 4 2 1 X",
        "2.2":         "2 2 1 X X X 1 X 1 X X 1 X 2 1 X X",
        "2.3":         "2 2 1 X X X 2 X 2 X X 2 X 2 1 X X",
        "3":           "4 4 2 2 1 2 X X 2 2 2 2 X 3 2 X X",
        "4.1":         "4 3 2 1 X X X X 1 X 1 2 X 3 2 1 X",
        "4.2":         "4 3 2 2 1 2 2 1 X 1 2 2 1 3 2 1 X",
        "4.3":         "4 4 2 2 X X 2 X 1 X 2 2 X 2 2 1 X",
        "5.1":         "4 4 2 2 X X 2 1 2 2 X 2 1 3 1 2 X",
        "5.2":         "4 4 2 2 1 2 2 2 2 2 2 X 1 3 2 2 X",
        "6.1":         "2 2 X X X X X X 1 X 1 1 X 1 X X X",
        "6.2":         "4 4 4 4 2 2 3 3 3 2 3 3 1 X 3 3 X",
        "7":           "2 2 2 2 1 1 2 2 2 2 1 2 X 3 X 2 X",
        "8":           "4 2 2 1 X X X 1 1 1 2 2 X 3 2 X X",
        "9":           "X X X X X X X X X X X X X X X X X",
    }
    rules = get_compliance_rules()["imdg_segregation"]
    assert rules["class_order"] == list(official)
    for row, expected in official.items():
        assert rules["table"][row] == expected.split(), row


def test_imdg_class1_compatibility_matches_7_2_7_1_4():
    """Toegestane gemengde stuwage per compatibiliteitsgroep (IMDG 7.2.7.1.4)."""
    rules = get_compliance_rules()["imdg_class1_compatibility"]
    order, matrix = rules["group_order"], rules["matrix"]
    assert order == ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "N", "S"]

    def permitted(a: str, b: str) -> bool:
        return matrix[a][order.index(b)] == "X"

    # Group S is compatible with everything except L.
    for group in order:
        assert permitted("S", group) is (group != "L"), group
    # L only with L (note 2).
    assert [g for g in order if permitted("L", g)] == ["L"]
    # C, D and E among themselves and with G and N.
    for group in ("C", "D", "E"):
        for other in ("C", "D", "E", "G", "N", "S"):
            assert permitted(group, other), f"{group}×{other}"
    # Incompatible: blasting explosive group D with detonators group B.
    assert not permitted("B", "D")
    assert not permitted("A", "B")
    # Symmetrie.
    for a in order:
        for b in order:
            assert permitted(a, b) == permitted(b, a), f"{a}×{b}"


def test_class1_compatibility_check_flags_incompatible_groups():
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            {"un_number": "0081", "proper_shipping_name": "SPRINGSTOF", "class": "1.1D",
             "classification_code": "1.1D"},
            {"un_number": "0029", "proper_shipping_name": "SLAGPIJPJES", "class": "1.1B",
             "classification_code": "1.1B"},
        ],
    }]
    warnings = check_imdg_class1_compatibility(entries, "nl")
    assert any(w["severity"] == "error" and "B × D" in w["rule"] or "D × B" in w["rule"] for w in warnings)


def test_subsidiary_class1_hazard_segregates_as_division_1_3():
    """IMDG 7.2.3.3: a subsidiary risk of class 1 counts as division 1.3."""
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            # Class 3 with subsidiary risk class 1 → has to be weighed as 1.3 against 4.1.
            {"un_number": "9990", "proper_shipping_name": "TESTSTOF", "class": "3",
             "subsidiary_risks": "1"},
            {"un_number": "1350", "proper_shipping_name": "ZWAVEL", "class": "4.1"},
        ],
    }]
    warnings = check_imdg_segregation(entries, "nl")
    # 1.3 × 4.1 = 3 in the table, stricter than 3 × 4.1 = X.
    assert warnings and warnings[0]["code"] == "3"


def test_segregation_groups_are_loaded_from_imdg_3_1_4_4():
    """All eighteen groups with their UN numbers from chapter 3.1."""
    seed = json.loads(
        (Path(__file__).resolve().parents[1] / "seed" / "dg" / "segregation_groups.json")
        .read_text(encoding="utf-8")
    )
    codes = [g["code"] for g in seed["groups"]]
    assert codes == [f"SGG{n}" for n in range(1, 19)]
    assert len(seed["by_un"]) >= 500

    # Hydrochloric acid belongs with the acids. The separate SGG1a marking for
    # strong acids lapsed with Amendment 41-22 and must not turn up anywhere.
    assert segregation_groups_for("1789") == ["SGG1"]
    assert not any("SGG1a" in codes for codes in seed["by_un"].values())
    assert segregation_groups_for("1824") == ["SGG18"]   # natronloog, alkali
    assert segregation_groups_for("1689") == ["SGG6"]    # natriumcyanide
    assert segregation_groups_for("1203") == []          # petrol falls outside the groups

    # Loodazide hoort in drie groepen tegelijk.
    assert set(segregation_groups_for("0129")) == {"SGG7", "SGG9", "SGG17"}


def test_segregation_group_conflicts_are_reported():
    """Acids with alkalis and acids with cyanides call for segregation."""
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            {"un_number": "1789", "proper_shipping_name": "ZOUTZUUR", "class": "8"},
            {"un_number": "1824", "proper_shipping_name": "NATRONLOOG", "class": "8"},
            {"un_number": "1689", "proper_shipping_name": "NATRIUMCYANIDE", "class": "6.1"},
        ],
    }]
    rules = {w["rule"] for w in check_imdg_segregation_groups(entries, "nl")}
    assert "IMDG 7.2.5 (SGG1 × SGG18)" in rules
    assert "IMDG 7.2.5 (SGG1 × SGG6)" in rules

    # Without conflicting groups it stays quiet.
    assert check_imdg_segregation_groups(
        [{"line_id": 1, "vehicle": "x", "products": [{"un_number": "1789"}]}], "nl"
    ) == []


def test_imdg_segregation_warns_for_incompatible_classes():
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            {"un_number": "1203", "proper_shipping_name": "BENZINE", "class": "3"},
            {"un_number": "2031", "proper_shipping_name": "SALPETERZUUR", "class": "8", "subsidiary_risks": "5.1"},
        ],
    }]
    warnings = check_imdg_segregation(entries, "nl")
    assert len(warnings) == 1
    # Class 3 × 5.1 = code 2 ("separated from"); a subsidiary risk counts.
    assert warnings[0]["code"] == "2"
    assert "Gescheiden van" in warnings[0]["message"]


def test_imdg_segregation_silent_for_compatible_classes():
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            {"un_number": "1203", "class": "3"},
            {"un_number": "1830", "class": "8"},
        ],
    }]
    # 3 × 8 = X in the table: no general segregation prescribed.
    assert check_imdg_segregation(entries, "nl") == []


def test_prepare_lists_class_specific_document_requirements():
    entries = [{
        "line_id": 1,
        "vehicle": "Radioactief",
        "products": [{"un_number": "2915"}],
    }]
    requirements = prepare_entries(entries, [], ["ADR", "IATA_DGR"], "nl")["requirements"]
    assert any("transportindex" in item for item in requirements)
    assert any("Shipper's Declaration" in item for item in requirements)
