"""Fixes B1–B9 from the DG specialist review of v1.31.0.

Each test pins one finding: the regression that was reported, and the behaviour
that replaced it. The numbering matches the analysis document.
"""
from app.services.dg.autofill import (
    adr_quantity,
    derive_product,
    description_line,
    prepare_entries,
)
from app.services.dg.compliance import (
    append_class8_pair_exception,
    check_adr_points,
    check_air_forbidden,
    check_compliance,
    check_lq_eq,
    check_q_value,
)
from app.services.dg.enrichment import enrich_un_entry


def _entry(products, vehicle="Positie 1"):
    return {"line_id": 1, "vehicle": vehicle, "products": products}


# --- B1: divisie 2.3 (chloor) is in de luchtvaart verboden -----------------


def test_b1_chlorine_with_table_a_class_2_is_air_forbidden():
    """Tabel A schrijft klasse '2'; de divisie zit in de etiketten."""
    extras = enrich_un_entry(
        {"un": "1017", "name_en": "Chlorine", "class": "2", "labels": "2.3+5.1+8"},
        "nl",
    )
    assert extras["air_forbidden"] is True
    assert "2.3" in extras["air_note"]


def test_b1_air_forbidden_check_reads_division_from_labels():
    entries = [_entry([{
        "un_number": "1017",
        "proper_shipping_name": "CHLORINE",
        "class": "2",
        "labels": "2.3+5.1+8",
    }])]
    warnings = check_air_forbidden(entries, "nl")
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "error"
    assert "2.3" in warnings[0]["rule"]


def test_b1_iata_compliance_stack_includes_air_forbidden():
    result = check_compliance(
        [_entry([{
            "un_number": "1017",
            "proper_shipping_name": "CHLORINE",
            "class": "2",
            "labels": "2.3",
        }])],
        ["IATA_DGR"],
    )
    assert any(
        "2.3" in f.get("rule", "")
        for f in result["iata_segregation"]
    )


# --- B2: Q alleen als M (maximum) is ingevuld ------------------------------


def test_b2_q_is_skipped_when_only_n_is_auto_filled():
    """De prepare-stap vult n uit de netto per collo; dat mag Q niet starten."""
    entries = [_entry([{
        "un_number": "1263",
        "class": "3",
        "q_net_quantity": "5",  # auto uit netto, geen M
    }])]
    assert check_q_value(entries) == []


def test_b2_q_runs_when_m_is_present():
    # Q geldt voor 'all packed in one': minstens twee componenten met M.
    entries = [_entry([
        {"un_number": "1263", "class": "3",
         "q_net_quantity": "3", "q_max_net_quantity": "5"},
        {"un_number": "1760", "class": "8",
         "q_net_quantity": "1", "q_max_net_quantity": "4"},
    ])]
    results = check_q_value(entries)
    assert len(results) == 1
    assert results[0]["q_value"] == 0.9  # 0.6 + 0.25 → 0.9


# --- B3: Tabel A-rij volgt de gekozen verpakkingsgroep ---------------------


def test_b3_multi_packing_group_without_choice_gets_a_note():
    derived = derive_product({"un_number": "1263"}, "nl", ["ADR"])
    assert "packing_group_note" in derived["hints"]
    assert "I" in derived["hints"]["packing_group_note"]
    assert "II" in derived["hints"]["packing_group_note"]


def test_b3_user_packing_group_selects_that_table_a_row():
    derived = derive_product(
        {"un_number": "1263", "packing_group": "III"}, "nl", ["ADR"]
    )
    # packing_group stond al op het product, dus niet in de patch — de rij-
    # afhankelijke velden wel, en die horen bij PG III (cat 3, E1).
    assert derived["patch"]["transport_category"] == "3"
    assert derived["patch"]["excepted_quantity"] == "E1"
    assert "packing_group_note" not in derived["hints"]


# --- B4: klasse 1 rekent met NEM, niet productmassa ------------------------


def test_b4_class1_points_use_net_explosive_mass():
    assert adr_quantity({
        "class": "1.4G",
        "net_mass_liters_per_package": "50 kg",
        "quantity_packages": "2",
        "net_explosive_mass": "12",
    }) == (12.0, "kg")


def test_b4_class1_without_nem_is_incomplete_not_product_mass():
    total, unit = adr_quantity({
        "class": "1.4G",
        "net_mass_liters_per_package": "50 kg",
        "quantity_packages": "2",
    })
    assert total is None
    assert unit == "kg"

    entries = [_entry([{
        "un_number": "0336",
        "proper_shipping_name": "FIREWORKS",
        "class": "1.4G",
        "transport_category": "4",
        "net_mass_liters_per_package": "50 kg",
        "quantity_packages": "2",
    }])]
    prepared = prepare_entries(entries, [], ["ADR"], "nl")["entries"]
    result = check_adr_points(prepared)
    assert result["status"] == "incomplete"


def test_b4_class1_document_line_carries_nem():
    line = description_line({
        "un_number": "0336",
        "proper_shipping_name": "FIREWORKS",
        "class": "1.4G",
        "packing_group": "",
        "quantity_packages": "10",
        "type_of_package": "dozen",
        "net_explosive_mass": "4,5",
    }, "ADR")
    assert "NEM 4.5 kg" in line


# --- B5: 8-tons LQ-markering 3.4.13/14 -------------------------------------


def test_b5_eight_tonne_lq_mark_is_warned():
    # 25 kg bruto × 400 colli = 10 000 kg > 8 t, binnen LQ-grenzen.
    result = check_lq_eq(
        [_entry([{
            "un_number": "1263",
            "proper_shipping_name": "PAINT",
            "class": "3",
            "packing_group": "II",
            "limited_quantity": "5 L",
            "excepted_quantity": "E2",
            "net_per_inner_packaging": "0,5 L",
            "gross_mass_per_package": "25 kg",
            "quantity_packages": "400",
        }])],
        language="nl",
        profiles=["ADR"],
    )
    assert any(w["rule"] == "ADR 3.4.13/3.4.14" for w in result["warnings"])


def test_b5_under_eight_tonnes_is_silent():
    result = check_lq_eq(
        [_entry([{
            "un_number": "1263",
            "class": "3",
            "limited_quantity": "5 L",
            "excepted_quantity": "E2",
            "net_per_inner_packaging": "0,5 L",
            "gross_mass_per_package": "20 kg",
            "quantity_packages": "100",
        }])],
        profiles=["ADR"],
    )
    assert not any(w["rule"] == "ADR 3.4.13/3.4.14" for w in result["warnings"])


# --- B6: IMDG 7.2.6.5 naast het betrokken klasse-8-paar --------------------


def test_b6_class8_pair_exception_is_appended_to_the_finding():
    entries = [_entry([
        {"un_number": "1789", "proper_shipping_name": "HYDROCHLORIC ACID",
         "class": "8", "packing_group": "II"},
        {"un_number": "1824", "proper_shipping_name": "SODIUM HYDROXIDE SOLUTION",
         "class": "8", "packing_group": "II"},
    ])]
    findings = [{
        "rule": "IMDG 7.2.1.7.2",
        "severity": "warning",
        "message": "scheiden",
        "products": "UN 1789 HYDROCHLORIC ACID  ×  UN 1824 SODIUM HYDROXIDE SOLUTION",
    }]
    extended = append_class8_pair_exception(entries, findings, "nl")
    assert any(f["rule"] == "IMDG 7.2.6.5" and f["severity"] == "info" for f in extended)
    assert findings[0] in extended  # de waarschuwing blijft staan


# --- B7: verboden stof uit punten en documentregels ------------------------


def test_b7_forbidden_substance_is_skipped_in_points_and_documents():
    entries = [_entry([{
        "un_number": "1798",
        "proper_shipping_name": "NITROHYDROCHLORIC ACID",
        "class": "8",
        "transport_category": "0",
        "adr_total_quantity": "10",
        "transport_forbidden": True,
    }])]
    points = check_adr_points(entries)
    assert points["forbidden_products"]
    assert points["total_points"] == 0.0
    assert points["rows"] == []

    prepared = prepare_entries(
        [{"line_id": 1, "vehicle": "Vat", "products": [{
            "un_number": "1798",
            "proper_shipping_name": "NITROHYDROCHLORIC ACID",
            "class": "8",
        }]}],
        [],
        ["ADR"],
        "nl",
    )
    assert prepared["entries"][0]["products"][0].get("transport_forbidden") is True
    assert prepared["document_lines"]["ADR"] == []


# --- B8: hints gefilterd op actieve profielen ------------------------------


def test_b8_imdg_hints_are_absent_on_a_pure_adr_prepare():
    result = prepare_entries(
        [{"line_id": 1, "vehicle": "Tank", "products": [{"un_number": "1017"}]}],
        [],
        ["ADR"],
        "nl",
    )
    hints = result["hints"]
    assert hints, "enrichment moet wél iets teruggeven"
    for hint in hints:
        assert not any(k.startswith("ems_") for k in hint)
        assert not any(k.startswith("imdg_") for k in hint)
        assert "air_forbidden" not in hint


def test_b8_air_forbidden_hint_appears_when_iata_is_active():
    result = prepare_entries(
        [{"line_id": 1, "vehicle": "Tank", "products": [{"un_number": "1017"}]}],
        [],
        ["IATA_DGR"],
        "nl",
    )
    assert any(h.get("air_forbidden") for h in result["hints"])


# --- B9: binnenverpakking alleen waar LQ of EQ een route is ----------------
# (UI-gedrag; de rekenlaag blijft incomplete melden als het veld wél gevuld is
#  bij LQ=0/E0. De frontend verbergt het veld — vastgelegd in de component.)


def test_b9_lq_zero_and_e0_still_assess_when_inner_is_sent():
    """De rekenlaag blijft eerlijk: 0/E0 + ingevulde binnenverpakking = not_permitted."""
    result = check_lq_eq(
        [_entry([{
            "un_number": "1051",
            "class": "6.1",
            "limited_quantity": "0",
            "excepted_quantity": "E0",
            "net_per_inner_packaging": "10 g",
        }])],
        profiles=["ADR"],
    )
    row = result["rows"][0]
    assert row["lq"]["status"] == "not_permitted"
    assert row["eq"]["status"] == "not_permitted"
