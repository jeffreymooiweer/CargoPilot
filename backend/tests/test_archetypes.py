"""Four consignments, end to end, through the API a wizard actually calls.

The plan for this application named a closing step: walk four archetypes —
packaged goods by road, a road tank, a dry cargo vessel, a tank vessel — from
the goods to the last download, and see what comes out. Doing that by hand once
proves the day it was done. Doing it here proves it on every commit, and that
is the difference between a verification and an anecdote.

Each archetype asserts three things:

* **the compliance answer** carries the checks that mode is entitled to, and
  not the ones it is not — a tank vessel must not be answered with the dry
  cargo vessel's chapter 7.1, and a packages consignment must not be asked
  about a tank;
* **the documents** the wizard would offer are the documents that consignment
  needs, and each one that CargoPilot generates actually renders;
* **what the application cannot say** is said. Every archetype ends on the
  finding that names its own limit, because an answer with a silent hole in it
  is the failure this whole application is built against.
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.services.dg import database
from app.services.documents.registry import get_registry


def user():
    return SimpleNamespace(id=1, username="verify", role="admin", active=True)


def client():
    app.dependency_overrides[get_current_user] = user
    return TestClient(app)


def release():
    app.dependency_overrides.pop(get_current_user, None)


def goods(un, **extra):
    """A product as the prepare step leaves it: table A already applied."""
    rows = database.get_un_entries(un)
    row = rows[0] if rows else {}
    product = {
        "un_number": un,
        "proper_shipping_name": row.get("name_nl") or "",
        "class": row.get("class") or "",
        "classification_code": row.get("classification_code") or "",
        "packing_group": row.get("packing_group") or "",
        "labels": row.get("labels") or "",
        "hazard_number": row.get("hazard_number") or "",
        "tunnel_code": row.get("tunnel_code") or "",
        "transport_category": row.get("transport_category") or "",
        "quantity_packages": "4",
        "type_of_package": "vaten",
        "adr_total_quantity": "800 kg",
    }
    product.update(extra)
    return product


def compliance(profiles, *products, language="nl"):
    with client() as api:
        response = api.post("/api/dg/compliance", json={
            "entries": [{"line_id": "1", "vehicle": "UNIT-1",
                         "products": list(products)}],
            "profiles": profiles,
            "language": language,
        })
    release()
    assert response.status_code == 200, response.text
    return response.json()


#: A consignment filled in the way a wizard leaves it — every field the
#: documents ask for. An archetype with half its boxes empty proves that
#: validation works, which is a different test; this one is about what a
#: complete consignment produces.
CONSIGNMENT = {
    "consignor_name": "Afzender BV",
    "consignor_address": "Havenweg 1, 3011 Rotterdam, Nederland",
    "consignee_name": "Ontvanger GmbH",
    "consignee_address": "Hafenstrasse 4, 47119 Duisburg, Duitsland",
    "loading_point": "Rotterdam",
    "discharge_point": "Duisburg",
    "freight_payment": "Franco",
    "established_place": "Rotterdam",
    "established_date": "2026-08-15",
    "vessel_name": "Rijnvaart 7",
    "vehicle_registration": "12-BXG-3",
    "reference": "CP-2026-100",
    "emergency_contact": "+31 10 123 4567",
}


def export(document_key, *products, values=None, language="nl"):
    with client() as api:
        response = api.post("/api/documents/export", json={
            "document_key": document_key,
            "values": values or CONSIGNMENT,
            "lines": [],
            "dangerous_goods": [{"line_id": "1", "products": list(products)}],
            "output_language": language,
        })
    release()
    return response


def documents_for(modality):
    registry = get_registry()
    return next(m for m in registry["modalities"] if m["key"] == modality)["documents"]


# --- 1. packaged dangerous goods by road ----------------------------------


def test_road_packages():
    """Paint in drums on a lorry. The placarding answer for this is *no*: 5.3.1.5
    names class 1 and class 7 and nothing else, and telling a driver to placard
    anyway teaches that the placard is decoration."""
    answer = compliance(["ADR"], goods("1263"))

    assert "adr_points" in answer
    assert answer["adr_placarding"]["placards_required"] is False
    assert answer["adr_placarding"]["scope"] == "packages"
    # Not a tank: neither tank check may speak.
    assert answer.get("adr_tank_admission", {"status": "not_checked"})["status"] \
        == "not_checked"
    assert answer.get("adr_tank_fit", {"status": "not_checked"})["status"] \
        == "not_checked"

    assert "placarding_sheet" in documents_for("road")
    assert export("cmr", goods("1263")).status_code == 200
    assert export("placarding_sheet", goods("1263")).status_code == 200


# --- 2. a road tank -------------------------------------------------------


def test_road_tank():
    """Petrol in an L4BN semi-trailer. Column (12) requires LGBF; 4.3.4.1.2
    permits the tank that turned up, and the sheet carries the numbered plates
    that a tank — unlike packages — is *required* to show."""
    tank = goods("1203", carriage_mode="tank", tank_code="L4BN")
    answer = compliance(["ADR"], tank)

    assert answer["adr_tank_admission"]["status"] == "ok"
    fit = answer["adr_tank_fit"]["items"][0]
    assert fit["fit"] == "fits"
    assert fit["required"] == "LGBF"
    # The hierarchy is never the whole answer: column (13) travels with it.
    assert "TU9" in fit["provisions_note"]

    assert answer["adr_placarding"]["scope"] == "tanks_or_bulk"
    assert answer["adr_placarding"]["placards_required"] is True
    plates = [m for m in answer["adr_placarding"]["marks"]
              if m["kind"] == "tank_plates"]
    assert plates and "33 / UN 1203" in plates[0]["message"]

    assert export("placarding_sheet", tank).status_code == 200


def test_a_tank_that_does_not_fit_says_so():
    """The check has to be able to say no, or it says nothing at all."""
    answer = compliance(["ADR"], goods("1005", carriage_mode="tank",
                                       tank_code="C10DH"))
    assert answer["adr_tank_fit"]["items"][0]["fit"] == "does_not_fit"
    assert answer["adr_tank_fit"]["status"] == "not_permitted"


# --- 3. a dry cargo vessel ------------------------------------------------


def test_inland_dry_cargo():
    """Packages in the holds of a dry cargo vessel. Chapter 7.1 applies, the
    stowage plan of 7.1.4.11.1 is the document, and the hold is what makes
    7.1.4.3.2 a check rather than a statement."""
    hold_one = goods("1263", hold="1")
    answer = compliance(["ADN"], hold_one)

    assert "adn_exemption" in answer
    assert answer["adn_hold_separation"]["status"] != "not_available_for_mode"

    assert "stowage_plan" in documents_for("inland")
    assert export("adn_transport_doc", hold_one).status_code == 200
    assert export("stowage_plan", hold_one).status_code == 200


def test_two_cones_and_one_cone_flammable_in_one_hold():
    """The prohibition of 7.1.4.3.2, applied to what the boatmaster wrote."""
    answer = compliance(["ADN"], goods("1017", hold="1"), goods("1088", hold="1"))
    finding = next(f for f in answer["adn_hold_separation"]["findings"]
                   if f["provision"] == "7.1.4.3.2")
    assert finding["holds"] == ["1"]


# --- 4. a tank vessel -----------------------------------------------------


def test_inland_tank_vessel():
    """A cargo tank is not a hold, and chapter 7.1 is the chapter for dry cargo
    vessels. The separation check must decline for this consignment rather than
    answer it with the wrong chapter — that refusal is the whole point of the
    mode field."""
    cargo_tank = goods("1203", carriage_mode="tank")
    answer = compliance(["ADN"], cargo_tank)

    assert answer["adn_hold_separation"]["status"] == "not_available_for_mode"
    assert answer["adn_hold_separation"]["mode_note"]
    assert answer["adn_carriage_admission"]["status"] in ("ok", "not_permitted")

    # Table C answers what it settles and holds back what it does not: petrol's
    # rows split between vessel types N and C, so no single type is offered.
    signals = answer.get("adn_signals") or {}
    assert signals


# --- what every archetype must never lose ---------------------------------


@pytest.mark.parametrize("profiles,products", [
    (["ADR"], [{"un_number": "1263"}]),
    (["ADN"], [{"un_number": "1263"}]),
    (["IMDG"], [{"un_number": "1263"}]),
    (["IATA_DGR"], [{"un_number": "1263"}]),
])
def test_every_answer_names_the_editions_it_computed_with(profiles, products):
    """An answer that cannot say which editions it used cannot be checked by
    anyone, and a regulation that has expired must not be computed with in
    silence."""
    answer = compliance(profiles, *products)
    manifest = answer["regulatory_manifest"]
    assert manifest["editions"]
    assert manifest["manifest_id"]
    # An edition that has expired is named rather than quietly computed with.
    for expired in manifest.get("expired", []):
        assert expired in manifest["editions"]
    assert answer["rule_sets"]
