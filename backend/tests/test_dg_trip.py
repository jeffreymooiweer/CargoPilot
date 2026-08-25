"""Groupage: the findings a per-consignment check can never produce.

Every one of these tests is a load that passes consignment by consignment and
fails as a vehicle. That is the whole subject — if a case reads the same apart
as together, it did not need this module.

The three provisions are unchanged; what changes is what they are handed. So
these tests assert the *combination*, not the arithmetic: the arithmetic has
its own tests in ``test_dg_compliance.py`` and re-asserting it here would only
mean two places to update when a factor changes.
"""
import pytest

from app.services.dg.trip import (
    LQ_DISPENSATION_T,
    UNIT_MAX_MASS_TRIGGER_T,
    check_trip,
)


def consignment(name, products):
    return {"name": name, "entries": [{"products": products}]}


def petrol(quantity):
    """Transport category 2, factor 3 — 200 L is 600 of the 1000 points."""
    return {"un_number": "1203", "proper_shipping_name": "BENZINE", "class": "3",
            "transport_category": "2", "adr_total_quantity": quantity}


def paint_lq(packages, quantity="0"):
    """A limited-quantities line: within column 7a, 20 kg gross per package.

    ``quantity`` is the ADR total for the points check, and defaults to "0" —
    which that check reads as *not filled in*, not as zero, and so reports the
    line incomplete. Tests that need a settled points result pass a real one.
    """
    return {"un_number": "1263", "proper_shipping_name": "VERF", "class": "3",
            "transport_category": "3", "adr_total_quantity": quantity,
            "limited_quantity": "5 L", "net_per_inner_packaging": "3 L",
            "gross_mass_per_package": "20", "quantity_packages": str(packages)}


# --- 1.1.3.6: the points are per transport unit, not per consignment ---


def test_two_exempt_consignments_are_not_an_exempt_vehicle():
    """The finding this whole phase exists for.

    Each customer stays under the 1000 and is told so, truthfully, on their own
    screen. Put both on one vehicle and the exemption is gone — orange plates,
    an ADR driver, the equipment of 8.1.5 — and nothing in the application said
    so before, because nothing in the application looked at the vehicle.
    """
    result = check_trip(
        [consignment("Klant A", [petrol("200")]),
         consignment("Klant B", [petrol("200")])],
        ["ADR"], "en")

    assert [c["exempt"] for c in result["consignments"]] == [True, True]
    assert result["adr_points"]["total_points"] == 1200
    assert result["adr_points"]["status"] == "above_threshold"

    lost = result["exemption_lost"]
    assert lost is not None
    assert lost["consignments"] == ["Klant A", "Klant B"]
    assert "1000" in lost["message"] and "1200" in lost["message"]


def test_a_load_that_stays_exempt_says_nothing_extra():
    """A warning that fires when nothing is wrong teaches people to ignore it."""
    result = check_trip(
        [consignment("Klant A", [petrol("100")]),
         consignment("Klant B", [petrol("100")])],
        ["ADR"], "en")
    assert result["adr_points"]["status"] == "exempt_possible"
    assert result["exemption_lost"] is None


def test_one_consignment_that_was_already_over_is_not_reported_as_a_loss():
    """Nothing was lost by combining: that consignment was never exempt.

    Reported as a plain points result instead, because "combining cost you the
    exemption" is false here and a false explanation is worse than none.
    """
    result = check_trip(
        [consignment("Klant A", [petrol("400")]),
         consignment("Klant B", [petrol("50")])],
        ["ADR"], "en")
    assert result["adr_points"]["status"] == "above_threshold"
    assert result["exemption_lost"] is None


def test_a_single_consignment_trip_can_lose_nothing():
    result = check_trip([consignment("Klant A", [petrol("400")])], ["ADR"], "en")
    assert result["exemption_lost"] is None


# --- 7.5.2: two customers who may not share a vehicle ---


def test_mixed_loading_is_checked_between_consignments():
    """Explosives from one customer, corrosives from another.

    Within one consignment this was always checked. Between two it was checked
    by nobody, which is exactly the case a groupage planner creates.
    """
    result = check_trip(
        [consignment("Klant A", [{"un_number": "0027", "class": "1.1D",
                                  "proper_shipping_name": "BUSKRUIT",
                                  "compatibility_group": "D"}]),
         consignment("Klant B", [{"un_number": "1830", "class": "8",
                                  "proper_shipping_name": "ZWAVELZUUR",
                                  "transport_category": "2",
                                  "adr_total_quantity": "100"}])],
        ["ADR"], "en")
    assert result["mixed_loading"], "class 1 beside class 8 must be reported"
    assert any("7.5.2" in (w.get("rule") or "") + (w.get("message") or "")
               for w in result["mixed_loading"])


def test_a_warning_names_the_consignment_it_belongs_to():
    """Two customers shipping the same substance produce the same label.

    "These may not travel together" is unusable if the reader cannot tell which
    pallet to take off, so the consignment name travels into the label.
    """
    result = check_trip(
        [consignment("Klant A", [{"un_number": "0027", "class": "1.1D",
                                  "proper_shipping_name": "BUSKRUIT",
                                  "compatibility_group": "D"}]),
         consignment("Klant B", [{"un_number": "1830", "class": "8",
                                  "proper_shipping_name": "ZWAVELZUUR"}])],
        ["ADR"], "en")
    printed = " ".join(w.get("products", "") + w.get("message", "")
                       for w in result["mixed_loading"])
    assert "Klant A" in printed and "Klant B" in printed
    # And the substance is still named beside it, not replaced by it.
    assert "UN 0027" in printed and "UN 1830" in printed


def test_a_single_consignment_reads_exactly_as_it_always_did():
    """The consignment tag must not leak into the ordinary flow.

    ``check_adr_mixed_loading`` is the same function the wizard calls with
    untagged entries; a trip of one must produce the identical text.
    """
    from app.services.dg.compliance import check_adr_mixed_loading

    products = [{"un_number": "0027", "class": "1.1D",
                 "proper_shipping_name": "BUSKRUIT", "compatibility_group": "D"},
                {"un_number": "1830", "class": "8",
                 "proper_shipping_name": "ZWAVELZUUR"}]
    alone = check_adr_mixed_loading([{"products": products}], "en", ["ADR"])
    as_trip = check_trip([{"name": "", "entries": [{"products": products}]}],
                         ["ADR"], "en")["mixed_loading"]
    # The unnamed consignment falls back to "#1"; strip it and the rest is equal.
    assert [w["message"] for w in as_trip] == [w["message"] for w in alone]


def test_the_caller_s_consignments_come_back_untouched():
    """Tagging is this module's business, not the caller's data's."""
    entry = {"products": [petrol("100")]}
    given = [{"name": "Klant A", "entries": [entry]}]
    check_trip(given, ["ADR"], "en")
    assert "consignment" not in entry
    assert given == [{"name": "Klant A", "entries": [entry]}]


# --- 3.4.13 / 3.4.14: three quantities that are easy to run together ---


def test_the_twelve_tonnes_is_the_vehicle_and_the_eight_is_the_cargo():
    """The distinction the consignment-level check had collapsed.

    3.4.13 turns on the transport unit's permitted maximum mass; 3.4.14 turns
    on the gross mass of the LQ packages. One is a property of the vehicle and
    the other of the load, and reading the 8 t as the requirement's trigger
    makes the app demand a mark on a van the provision never reaches.
    """
    assert UNIT_MAX_MASS_TRIGGER_T == 12.0
    assert LQ_DISPENSATION_T == 8.0

    # Quantities stated, so the points check settles and the load is known to
    # be exempt — which means no orange plates, which leaves 3.4.13 to decide
    # on the two masses alone. That is what this test is about.
    load = [consignment("A", [paint_lq(250, quantity="5")]),
            consignment("B", [paint_lq(250, quantity="5")])]

    small = check_trip(load, ["ADR"], "en", unit_max_mass_tonnes=10.0)["lq_marking"]
    assert small["lq_gross_kg"] == 10_000
    assert small["over_dispensation"] is True
    assert small["required"] is False
    assert small["reason"] == "unit_at_or_below_12t"

    big = check_trip(load, ["ADR"], "en", unit_max_mass_tonnes=18.0)["lq_marking"]
    assert big["orange_plates_required"] is False
    assert big["required"] is True
    assert big["reason"] == "required"


def test_under_eight_tonnes_the_mark_may_be_dispensed_with():
    load = [consignment("A", [paint_lq(100)])]  # 2 000 kg
    marking = check_trip(load, ["ADR"], "en", unit_max_mass_tonnes=18.0)["lq_marking"]
    assert marking["lq_gross_kg"] == 2_000
    assert marking["over_dispensation"] is False
    assert marking["required"] is False
    assert marking["reason"] == "within_8t_dispensation"


def test_orange_plates_excuse_the_limited_quantities_mark():
    """3.4.13's own exception, and it is decidable only over the whole load.

    Two LQ consignments alone would need the mark. Add a third consignment of
    full-ADR goods and the unit carries orange plates under 5.3.2 — and then
    3.4.13 does not ask for the LQ mark at all. No single consignment can reach
    that conclusion, because no single consignment knows what else is aboard.
    """
    lq_only = check_trip(
        [consignment("A", [paint_lq(250)]), consignment("B", [paint_lq(250)])],
        ["ADR"], "en", unit_max_mass_tonnes=18.0)
    assert lq_only["lq_marking"]["reason"] == "required_unless_plates"

    with_plates = check_trip(
        [consignment("A", [paint_lq(250)]), consignment("B", [paint_lq(250)]),
         consignment("C", [petrol("500")])],
        ["ADR"], "en", unit_max_mass_tonnes=18.0)
    marking = with_plates["lq_marking"]
    assert marking["orange_plates_required"] is True
    assert marking["required"] is False
    assert marking["reason"] == "orange_plates_instead"


def test_without_the_vehicle_mass_the_marking_is_undecided_not_guessed():
    """The one number the application cannot derive, and does not invent.

    Reporting "not required" would be a certainty it has not got; reporting
    "required" would put a mark on every van. It asks instead.
    """
    marking = check_trip(
        [consignment("A", [paint_lq(250)]), consignment("B", [paint_lq(250)])],
        ["ADR"], "en")["lq_marking"]
    assert marking["required"] is None
    assert marking["reason"] == "unit_mass_unknown"
    assert "12" in marking["message"]


def test_a_total_past_the_threshold_is_past_it_whatever_is_missing():
    """``incomplete`` must not swallow a load that is already over.

    An LQ line states no ADR quantity, so the points check reports incomplete.
    With 1500 points already counted, treating that as undecided would have
    left the orange-plate question open on a load that plainly needs plates.
    """
    result = check_trip(
        [consignment("A", [paint_lq(250)]), consignment("C", [petrol("500")])],
        ["ADR"], "en", unit_max_mass_tonnes=18.0)
    assert result["adr_points"]["status"] == "incomplete"
    assert result["adr_points"]["total_points"] > result["adr_points"]["threshold"]
    assert result["lq_marking"]["orange_plates_required"] is True


# --- what a trip is, and is not ---


def test_the_result_carries_no_identifier_to_retrieve_it_by():
    """A trip is a calculation, not an entity.

    Privacy levels 1 and 2 store nothing about shipments. An id in this answer
    would be the first sign that something had been kept, so its absence is
    asserted rather than assumed.
    """
    result = check_trip([consignment("A", [petrol("100")])], ["ADR"], "en")
    assert not {"id", "trip_id", "uuid", "created_at"} & set(result)


def test_nothing_in_the_service_writes_to_a_database():
    """A sweep, because the promise is easier to break than to notice."""
    import pathlib

    source = (pathlib.Path(__file__).resolve().parents[1]
              / "app" / "services" / "dg" / "trip.py").read_text()
    for forbidden in ("Session", "get_db", "commit(", "sqlalchemy"):
        assert forbidden not in source, forbidden


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_every_finding_speaks_all_four_languages(language):
    result = check_trip(
        [consignment("A", [petrol("200")]), consignment("B", [petrol("200")])],
        ["ADR"], language, unit_max_mass_tonnes=18.0)
    assert result["exemption_lost"]["message"].strip()
    assert result["lq_marking"]["message"].strip()
