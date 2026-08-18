"""ADN 5.3: what the cargo transport units on board must show.

Read in the ADN 2025 English edition (printed pages 309-321, quoted by
scripts/read_land_regulations.py --doc adn) and sections 5.3.1 to 5.3.6 of the
official Dutch edition, which agree on every provision cited.

The shape of the answer follows from what the application cannot see: the kind
of cargo transport unit. A container is placarded for any class (5.3.1.2), a
wagon carrying packages likewise (5.3.1.5.3), a road vehicle carrying packages
only for Classes 1 and 7 (5.3.1.5.1/5.3.1.5.2) — except that the note to
5.3.1.5.2 placards it for every class when the ADN journey precedes a voyage
by sea. So the label models are computed once and the placement rules are
given per kind, each under its own provision.
"""

from app.services.dg.compliance import check_adn_placarding, check_compliance


def line(line_id, **product):
    return {"line_id": line_id, "products": [product]}


GASOLINE = {"un_number": "1203", "proper_shipping_name": "GASOLINE",
            "class": "3", "packing_group": "II", "labels": "3"}
ANILINE = {"un_number": "1547", "proper_shipping_name": "ANILINE",
           "class": "6.1", "packing_group": "II", "labels": "6.1"}


def provisions(result):
    return [p["provision"] for p in result["placards"]] + \
        [m["provision"] for m in result["marks"]]


def test_the_label_models_come_from_the_columns():
    result = check_adn_placarding([line("L1", **GASOLINE), line("L2", **ANILINE)])
    models = next(p for p in result["placards"] if p["provision"] == "5.3.1.1.1")
    assert models["label_models"] == ["3", "6.1"]
    assert result["placards_required"] is True


def test_every_ctu_kind_gets_its_own_rule():
    result = check_adn_placarding([line("L1", **GASOLINE)])
    found = provisions(result)
    assert "5.3.1.2" in found        # containers: any class, both sides + ends
    assert "5.3.1.5.3" in found      # wagons: any class, both sides
    assert "5.3.1.5.2" in found      # vehicles: none for class 3 — except sea


def test_a_vehicle_without_class_1_or_7_is_told_about_the_sea_note():
    result = check_adn_placarding([line("L1", **GASOLINE)])
    vehicle = next(p for p in result["placards"] if p["provision"] == "5.3.1.5.2")
    assert "5.3.1.5.2" in vehicle["message"]
    assert vehicle.get("required") is not True


def test_class_1_places_placards_on_the_vehicle_too():
    explosive = {"un_number": "0331", "proper_shipping_name": "EXPLOSIVE 1.5D",
                 "class": "1", "classification_code": "1.5D", "labels": "1.5"}
    result = check_adn_placarding([line("L1", **explosive)])
    vehicle = next(p for p in result["placards"]
                   if p["provision"] == "5.3.1.5.1/5.3.1.5.2")
    assert vehicle["required"] is True
    models = next(p for p in result["placards"] if p["provision"] == "5.3.1.1.1")
    assert "1.5D" in models["label_models"]


def test_division_15_beside_12_is_placarded_as_11():
    """5.3.1.1.2's own escalation, spelled out in both editions."""
    a = {"un_number": "0331", "class": "1", "classification_code": "1.5D",
         "proper_shipping_name": "A", "labels": "1.5"}
    b = {"un_number": "0004", "class": "1", "classification_code": "1.2B",
         "proper_shipping_name": "B", "labels": "1"}
    result = check_adn_placarding([line("L1", **a), line("L2", **b)])
    aggregated = next(p for p in result["placards"] if p["provision"] == "5.3.1.1.2")
    assert "1.1" in aggregated["message"]
    models = next(p for p in result["placards"] if p["provision"] == "5.3.1.1.1")
    assert "1.1" in models["label_models"]


def test_14s_alone_needs_no_class_1_placard():
    s = {"un_number": "0014", "class": "1", "classification_code": "1.4S",
         "proper_shipping_name": "CARTRIDGES", "labels": "1.4"}
    result = check_adn_placarding([line("L1", **s)])
    models = [p for p in result["placards"] if p["provision"] == "5.3.1.1.1"]
    assert not models or all("1.4" not in m for m in models[0]["label_models"])


def test_label_9a_becomes_model_9():
    battery = {"un_number": "3480", "proper_shipping_name": "LITHIUM ION BATTERIES",
               "class": "9", "labels": "9A"}
    result = check_adn_placarding([line("L1", **battery)])
    models = next(p for p in result["placards"] if p["provision"] == "5.3.1.1.1")
    assert models["label_models"] == ["9"]
    assert "9A" not in models["label_models"]


def test_a_cargo_tank_consignment_is_named_not_answered():
    tank = dict(GASOLINE, carriage_mode="tank")
    result = check_adn_placarding([line("L1", **tank)])
    assert result["status"] == "not_available_for_mode"
    assert result["mode_note"]
    assert result["placards"] == []


def test_a_portable_tank_gets_the_numbered_plates():
    tank = dict(GASOLINE, carriage_mode="portable_tank", hazard_number="33")
    result = check_adn_placarding([line("L1", **tank)])
    plates = next(m for m in result["marks"] if m["kind"] == "tank_plates")
    assert "33 / UN 1203" in plates["message"]
    assert result["scope"] == "tanks_or_bulk"


def test_the_exemption_note_is_reported_not_granted():
    small = dict(GASOLINE, adr_total_quantity="100")
    result = check_adn_placarding([line("L1", **small)],
                                  exemption_status="exempt_possible")
    note = next(m for m in result["marks"] if m["kind"] == "exempt_note")
    assert note["provision"] == "1.1.3.6.2"
    # The full answer still stands beside it: over-signalling is the safe
    # direction to be wrong in.
    assert result["placards_required"] is True


def test_the_environmental_mark_hangs_on_the_placard():
    green = dict(GASOLINE, environmentally_hazardous=True)
    result = check_adn_placarding([line("L1", **green)])
    mark = next(m for m in result["marks"] if m["kind"] == "environmental_mark")
    assert mark["provision"] == "5.3.6.1"


def test_check_compliance_carries_the_result_for_inland():
    out = check_compliance([line("L1", **GASOLINE)], ["ADN"], "en")
    assert out["adn_placarding"]["status"] == "ok"
    out = check_compliance([line("L1", **GASOLINE)], ["ADR"], "en")
    assert "adn_placarding" not in out


def test_every_language_speaks():
    for language in ("nl", "en", "de", "fr"):
        result = check_adn_placarding(
            [line("L1", **GASOLINE), line("L2", **ANILINE)], language)
        assert all(p["message"] for p in result["placards"])
        assert all(m["message"] for m in result["marks"])
