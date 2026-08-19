"""RID 5.3: what the wagons and large containers on the rail leg must show.

Read in the RID 2025 English edition (printed pages 837-845 and the column (5)
explanation of 3.2.1 on page 258, quoted by scripts/read_land_regulations.py
--doc rid) and the German edition, which agree on every provision cited.

Three things make the rail answer its own rather than the road's on loan: a
wagon carrying packages is placarded for every class (5.3.1.5); the orange
plates attach only where column (20) gives a hazard identification number
(5.3.2.1.1) - there are no plain front-and-rear plates on rail; and the
shunting labels of 5.3.4 are only ever affixed for Class 1 full-load wagons
and Class 2 tank-type wagons, with the per-substance bracketed model sitting
in RID's own column (5), which this application does not hold.
"""

from app.services.dg.compliance import check_compliance, check_rid_placarding


def line(line_id, **product):
    return {"line_id": line_id, "products": [product]}


GASOLINE = {"un_number": "1203", "proper_shipping_name": "GASOLINE",
            "class": "3", "packing_group": "II", "labels": "3",
            "hazard_number": "33"}
CHLORINE = {"un_number": "1017", "proper_shipping_name": "CHLORINE",
            "class": "2", "classification_code": "2TOC", "labels": "2.3, 5.1, 8",
            "hazard_number": "268"}


def provisions(result):
    return [p["provision"] for p in result["placards"]] + \
        [m["provision"] for m in result["marks"]]


def test_a_package_wagon_placards_for_every_class():
    """5.3.1.5 — the rule the road does not have: petrol in packages placards
    the wagon, where a road vehicle with the same packages placards nothing."""
    result = check_rid_placarding([line("L1", **GASOLINE)])
    wagon = next(p for p in result["placards"] if p["provision"] == "5.3.1.5")
    assert wagon["required"] is True
    assert result["placards_required"] is True


def test_no_plain_orange_plates_on_rail():
    """A packages consignment of several substances gets no orange-plate
    requirement at all — RID has no 5.3.2.1.1 front-and-rear plates."""
    aniline = {"un_number": "1547", "proper_shipping_name": "ANILINE",
               "class": "6.1", "labels": "6.1", "hazard_number": "60"}
    result = check_rid_placarding([
        line("L1", **GASOLINE), line("L2", **aniline)])
    kinds = [m["kind"] for m in result["marks"]]
    assert "orange_plates" not in kinds


def test_a_single_substance_full_load_gets_the_permission():
    result = check_rid_placarding([line("L1", **GASOLINE)])
    mark = next(m for m in result["marks"] if m["kind"] == "orange_plates")
    assert mark["required"] is None
    assert "5.3.2.1.1" in mark["provision"]


def test_a_tank_wagon_gets_the_numbered_plates():
    tank = dict(GASOLINE, carriage_mode="tank")
    result = check_rid_placarding([line("L1", **tank)])
    mark = next(m for m in result["marks"]
                if m["kind"] == "orange_plates" and m.get("required") is True)
    assert "33 / UN 1203" in mark["message"]
    assert result["scope"] == "tanks_or_bulk"


def test_a_tank_without_a_hazard_number_is_said_not_guessed():
    tank = dict(GASOLINE, carriage_mode="tank", hazard_number="")
    result = check_rid_placarding([line("L1", **tank)])
    mark = next(m for m in result["marks"] if m["kind"] == "orange_plates")
    assert mark["required"] is None


def test_a_substance_with_the_bracketed_model_is_named():
    """Chlorine's column (5) brackets (+13) — read in the English and German
    editions, which agree — so the finding names the substance and its model
    instead of hedging at the whole class."""
    tank = dict(CHLORINE, carriage_mode="tank")
    result = check_rid_placarding([line("L1", **tank)])
    shunt = next(m for m in result["marks"] if m["kind"] == "shunting_labels")
    assert shunt["required"] is None
    assert "1017" in shunt["message"] and "13" in shunt["message"]


def test_a_trigger_class_without_the_model_is_told_so():
    """UN 0331 is class 1 and used to get the hedge; its column (5) brackets
    no model in either edition, and a real absence is an answer."""
    explosive = {"un_number": "0331", "proper_shipping_name": "EXPLOSIVE",
                 "class": "1", "classification_code": "1.5D", "labels": "1.5"}
    result = check_rid_placarding([line("L1", **explosive)])
    shunt = next(m for m in result["marks"] if m["kind"] == "shunting_labels")
    assert shunt["required"] is False


def test_black_powder_carries_model_13():
    powder = {"un_number": "0027", "proper_shipping_name": "BLACK POWDER",
              "class": "1", "classification_code": "1.1D", "labels": "1"}
    result = check_rid_placarding([line("L1", **powder)])
    shunt = next(m for m in result["marks"] if m["kind"] == "shunting_labels")
    assert shunt["required"] is None
    assert "0027" in shunt["message"]


def test_packaged_class_3_raises_no_shunting_condition():
    result = check_rid_placarding([line("L1", **GASOLINE)])
    assert all(m["kind"] != "shunting_labels" for m in result["marks"])


def test_the_orange_band_follows_the_state_of_the_gas():
    """5.3.5 turns on liquefied (2), refrigerated liquefied (3) or dissolved
    (4) - the first digit of the classification code. Chlorine is 2TOC."""
    tank = dict(CHLORINE, carriage_mode="tank")
    result = check_rid_placarding([line("L1", **tank)])
    band = next(m for m in result["marks"] if m["kind"] == "orange_band")
    assert band["required"] is True


def test_a_compressed_gas_gets_no_band():
    compressed = {"un_number": "1002", "proper_shipping_name": "AIR COMPRESSED",
                  "class": "2", "classification_code": "1A", "labels": "2.2",
                  "carriage_mode": "tank", "hazard_number": "20"}
    result = check_rid_placarding([line("L1", **compressed)])
    assert all(m["kind"] != "orange_band" for m in result["marks"])


def test_division_15_beside_12_is_placarded_as_11():
    a = {"un_number": "0331", "class": "1", "classification_code": "1.5D",
         "proper_shipping_name": "A", "labels": "1.5"}
    b = {"un_number": "0004", "class": "1", "classification_code": "1.2B",
         "proper_shipping_name": "B", "labels": "1"}
    result = check_rid_placarding([line("L1", **a), line("L2", **b)])
    aggregated = next(p for p in result["placards"] if p["provision"] == "5.3.1.1.2")
    assert "1.1" in aggregated["message"]


def test_check_compliance_carries_the_result_for_rail_only():
    out = check_compliance([line("L1", **GASOLINE)], ["RID"], "en")
    assert out["rid_placarding"]["status"] == "ok"
    out = check_compliance([line("L1", **GASOLINE)], ["ADR"], "en")
    assert "rid_placarding" not in out


def test_every_language_speaks():
    for language in ("nl", "en", "de", "fr"):
        result = check_rid_placarding(
            [line("L1", **dict(CHLORINE, carriage_mode="tank"))], language)
        assert all(p["message"] for p in result["placards"])
        assert all(m["message"] for m in result["marks"])
