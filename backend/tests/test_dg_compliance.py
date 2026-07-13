from app.services.dg.compliance import (
    check_adr_mixed_loading,
    check_adr_points,
    check_compliance,
    check_iata_segregation,
    check_q_value,
)


def _entry(products, vehicle="Positie 1"):
    return {"line_id": 1, "vehicle": vehicle, "products": products}


def test_adr_points_exempt_below_threshold():
    entries = [_entry([
        {"un_number": "1203", "proper_shipping_name": "BENZINE", "class": "3",
         "transport_category": "2", "adr_total_quantity": "300"},
    ])]
    result = check_adr_points(entries)
    assert result["rows"][0]["points"] == 900.0
    assert result["total_points"] == 900.0
    assert result["status"] == "exempt_possible"
    assert result["exempt_provisions"]


def test_adr_points_above_threshold():
    entries = [_entry([
        {"un_number": "1203", "class": "3", "transport_category": "2", "adr_total_quantity": 300},
        {"un_number": "1263", "class": "3", "transport_category": "3", "adr_total_quantity": 200},
    ])]
    result = check_adr_points(entries)
    assert result["total_points"] == 1100.0
    assert result["status"] == "above_threshold"


def test_adr_points_category0_blocks_exemption():
    entries = [_entry([
        {"un_number": "1051", "class": "6.1", "transport_category": "0", "adr_total_quantity": 1},
    ])]
    result = check_adr_points(entries)
    assert result["status"] == "not_exempt"
    assert result["category0_products"]


def test_adr_points_incomplete_when_category_missing():
    entries = [_entry([{"un_number": "1203", "class": "3", "adr_total_quantity": 10}])]
    result = check_adr_points(entries)
    assert result["status"] == "incomplete"
    assert result["incomplete_products"]


def test_adr_points_category4_counts_zero():
    entries = [_entry([
        {"un_number": "3373", "class": "6.2", "transport_category": "4", "adr_total_quantity": 500},
    ])]
    result = check_adr_points(entries)
    assert result["total_points"] == 0.0
    assert result["status"] == "exempt_possible"


def test_mixed_loading_class1_with_other_classes():
    entries = [_entry([
        {"un_number": "0331", "class": "1.5D"},
        {"un_number": "1203", "class": "3"},
    ])]
    warnings = check_adr_mixed_loading(entries)
    assert any(w["rule"] == "ADR 7.5.2.1" for w in warnings)


def test_mixed_loading_14s_is_exempt():
    entries = [_entry([
        {"un_number": "0012", "class": "1.4S"},
        {"un_number": "1203", "class": "3"},
    ])]
    warnings = check_adr_mixed_loading(entries)
    assert not any(w["rule"] == "ADR 7.5.2.1" for w in warnings)


def test_mixed_loading_cv28_foodstuffs():
    entries = [_entry([{"un_number": "1547", "class": "6.1"}])]
    warnings = check_adr_mixed_loading(entries)
    assert any("CV28" in w["rule"] for w in warnings)


def test_iata_segregation_class1_with_flammable_liquid():
    entries = [_entry([
        {"un_number": "0331", "class": "1.5D"},
        {"un_number": "1203", "class": "3"},
    ])]
    warnings = check_iata_segregation(entries)
    assert warnings
    assert "1" in warnings[0]["rule"]


def test_iata_segregation_class8_with_43():
    entries = [_entry([
        {"un_number": "1428", "class": "4.3"},
        {"un_number": "1789", "class": "8"},
    ])]
    warnings = check_iata_segregation(entries)
    assert any("4.3" in w["rule"] and "8" in w["rule"] for w in warnings)


def test_iata_segregation_lithium_with_flammable():
    entries = [_entry([
        {"un_number": "3480", "class": "9"},
        {"un_number": "1203", "class": "3"},
    ])]
    warnings = check_iata_segregation(entries)
    assert any("lithium" in w["rule"].lower() for w in warnings)


def test_iata_no_segregation_for_compatible_classes():
    entries = [_entry([
        {"un_number": "1263", "class": "3"},
        {"un_number": "1789", "class": "8"},
    ])]
    warnings = check_iata_segregation(entries)
    assert warnings == []


def test_q_value_calculation_and_exceeded():
    entries = [_entry([
        {"un_number": "1263", "proper_shipping_name": "PAINT", "class": "3",
         "q_net_quantity": "3", "q_max_net_quantity": "5"},
        {"un_number": "1760", "proper_shipping_name": "CORROSIVE LIQUID", "class": "8",
         "q_net_quantity": "2", "q_max_net_quantity": "4"},
    ])]
    results = check_q_value(entries)
    assert len(results) == 1
    assert results[0]["q_value"] == 1.1  # 0.6 + 0.5 = 1.1
    assert results[0]["exceeded"] is True


def test_q_value_within_limit():
    entries = [_entry([
        {"class": "3", "q_net_quantity": "1", "q_max_net_quantity": "5"},
        {"class": "8", "q_net_quantity": "1", "q_max_net_quantity": "4"},
    ])]
    results = check_q_value(entries)
    assert results[0]["q_value"] == 0.5  # 0.2 + 0.25 = 0.45 -> 0.5 naar boven
    assert results[0]["exceeded"] is False


def test_check_compliance_profiles():
    entries = [_entry([
        {"un_number": "1203", "class": "3", "transport_category": "2",
         "adr_total_quantity": 100, "cargo_aircraft_only": "Y"},
    ])]
    result = check_compliance(entries, ["ADR", "IATA_DGR"])
    assert "adr_points" in result
    assert "adr_mixed_loading" in result
    assert "iata_segregation" in result
    assert result["cargo_aircraft_only_products"]

    adr_only = check_compliance(entries, ["ADR"])
    assert "iata_segregation" not in adr_only
