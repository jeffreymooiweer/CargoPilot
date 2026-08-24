"""The way back: what a return carries over, and what it must not.

Copying the outward consignment is the easy half. Knowing what may not be
copied is the work, and every assertion here that a field comes back empty is
guarding against a number that would be false on the return — an empty drum
that still says 200 litres, on a form somebody signs.
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.services.dg.compliance import check_adr_points
from app.services.dg.return_shipment import (
    JOURNEY_FIELDS,
    QUANTITY_FIELDS,
    return_shipment,
)

OUTWARD_VALUES = {
    "consignor_name": "Afzender BV",
    "consignor_address": "Industrieweg 1, Wezep",
    "consignor_contact": "J. Mooiweer",
    "consignee_name": "Klant NV",
    "consignee_address": "Havenweg 9, Rotterdam",
    "consignee_contact": "A. de Vries",
    "shipment_reference": "CP-2026-500",
    "loading_date": "2026-08-24",
    "consignor_declarations": "signed",
    "signature_image": "data:image/png;base64,AAAA",
}


def outward_product(**over):
    product = {
        "un_number": "1263", "proper_shipping_name": "VERF", "class": "3",
        "packing_group": "II", "transport_category": "2",
        "adr_total_quantity": "300", "net_mass_liters_per_package": "20",
        "net_per_inner_packaging": "5", "gross_mass_per_package": "24",
        "quantity_packages": "15", "type_of_package": "drum",
    }
    product.update(over)
    return product


def turned(**over):
    values = dict(OUTWARD_VALUES)
    values.update(over)
    return return_shipment(
        values, [], [{"line_id": "1", "products": [outward_product()]}])


# --- the parties ---


def test_the_filler_receives_what_they_sent():
    result = turned()
    assert result["values"]["consignor_name"] == "Klant NV"
    assert result["values"]["consignee_name"] == "Afzender BV"


def test_the_addresses_and_contacts_travel_with_their_party():
    result = turned()["values"]
    assert result["consignor_address"] == "Havenweg 9, Rotterdam"
    assert result["consignee_address"] == "Industrieweg 1, Wezep"
    assert result["consignor_contact"] == "A. de Vries"
    assert result["consignee_contact"] == "J. Mooiweer"


# --- what is set ---


def test_every_line_becomes_empty_uncleaned():
    products = turned()["dangerous_goods"][0]["products"]
    assert all(p["empty_uncleaned"] for p in products)


def test_the_substance_stays_because_the_residue_is_described_by_it():
    """5.4.1.1.6.1 describes what is in the drum by the goods that were."""
    product = turned()["dangerous_goods"][0]["products"][0]
    assert product["un_number"] == "1263"
    assert product["proper_shipping_name"] == "VERF"
    assert product["class"] == "3"


# --- what must not come back ---


def test_no_quantity_survives_the_turn():
    """Each of these would be a number that is not true on the way back."""
    product = turned()["dangerous_goods"][0]["products"][0]
    for field in QUANTITY_FIELDS:
        assert not product.get(field), field


def test_the_number_of_packages_does_survive():
    """The same drums come back. That one is not a lie."""
    assert turned()["dangerous_goods"][0]["products"][0]["quantity_packages"] == "15"


def test_nothing_about_this_journey_survives():
    result = turned()["values"]
    for field in JOURNEY_FIELDS:
        assert not result.get(field), field


def test_the_declaration_and_the_signature_do_not_come_along():
    """Both were given for the outward goods. Carrying them onto a different
    consignment would put somebody's name under something they never saw."""
    result = turned()["values"]
    assert "consignor_declarations" not in result
    assert not result["signature_image"]


# --- and the outward shipment is not disturbed ---


def test_the_outward_consignment_is_left_alone():
    """The wizard may still be showing it. A transformation that mutated its
    input would empty the screen the user is looking at."""
    entries = [{"line_id": "1", "products": [outward_product()]}]
    return_shipment(dict(OUTWARD_VALUES), [], entries)
    assert entries[0]["products"][0]["adr_total_quantity"] == "300"
    assert not entries[0]["products"][0].get("empty_uncleaned")


# --- and the checks answer it as they answer anything else ---


def test_the_returned_load_counts_nothing_towards_the_thousand():
    """The point of the whole thing, end to end: 1.1.3.6.1 reassigns an empty
    uncleaned packaging to transport category 4, and the return produced by
    this module is what feeds that. Outward the same drums are 900 points."""
    outward = check_adr_points(
        [{"line_id": "1", "products": [outward_product()]}])
    back = check_adr_points(turned()["dangerous_goods"])
    assert outward["total_points"] == 900.0
    assert back["total_points"] == 0.0
    assert back["rows"][0]["transport_category"] == "4"


# --- through the route the wizard calls ---


def test_the_route_turns_a_shipment_round():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="verify", role="admin", active=True)
    with TestClient(app) as api:
        response = api.post("/api/dg/return", json={
            "values": OUTWARD_VALUES,
            "lines": [],
            "dangerous_goods": [
                {"line_id": "1", "products": [outward_product()]}],
        })
    app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["values"]["consignor_name"] == "Klant NV"
    assert body["dangerous_goods"][0]["products"][0]["empty_uncleaned"] is True
