"""The customs references whose condition the route decides.

The ENS reference applies to goods entering the EU customs territory, the AES
ITN to exports from the United States. Both conditions used to live in a
tooltip, and the person filling in the form decided. Now the route decides
where it can, and says on what ground; where it cannot, it says nothing, and
the question stays where it was.

The places pinned here are read out of the location seed the interface picks
from, so a verdict is tested against the same text a user's screen produces.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.services.documents import get_document, validate_document
from app.services.documents.customs_route import (
    EU_CUSTOMS_TERRITORY,
    Place,
    assess,
    read_place,
)


def picked(name: str, code: str, region: str) -> str:
    """What GeoInputs.formatLocation writes into the field."""
    return f"{name} ({code}), {region}"


# --- reading a route end ----------------------------------------------------


@pytest.mark.parametrize("text,country", [
    (picked("Rotterdam", "NLRTM", "ZH, NL"), "NL"),
    (picked("New York", "USNYC", "NY, US"), "US"),
    (picked("San Juan", "PRSJU", "PR"), "PR"),
    (picked("Saint Thomas", "VISTT", "VI"), "VI"),
    (picked("Montreal", "CAMTR", "QC, CA"), "CA"),
    (picked("Amsterdam Airport Schiphol", "AMS", "Amsterdam, NL"), "NL"),
    (picked("John F. Kennedy International Airport", "JFK", "New York, US"), "US"),
    (picked("Graz Hbf", "8103171", "AT"), "AT"),
    (picked("Monaco", "MCMON", "MC"), "MC"),
    (picked("Thorshavn", "FOTHO", "FO"), "FO"),
])
def test_a_picked_location_is_read_by_its_code(text, country):
    assert read_place(text) == Place(country)


@pytest.mark.parametrize("text,country", [
    ("Keizersgracht 1\n1015 CD Amsterdam\nNetherlands", "NL"),
    ("1600 Pennsylvania Avenue, Washington, United States", "US"),
    ("Hauptstraße 5, 10115 Berlin, Deutschland", "DE"),
    ("12 rue de Rivoli, 75001 Paris, France", "FR"),
    ("Rotterdam, NL", "NL"),
    ("Antwerpen, Belgie", "BE"),
    ("Basel, Zwitserland", "CH"),
    ("Oslo, Norway", "NO"),
    ("Toronto, Kanada", "CA"),
    ("Charlotte Amalie, Amerikaanse Maagdeneilanden", "VI"),
    ("Şişli, Istanbul, Türkiye", "TR"),
])
def test_an_address_or_free_text_is_read_by_its_country_name(text, country):
    assert read_place(text) == Place(country)


def test_a_longer_name_wins_over_a_shorter_one_it_contains():
    # "Ireland" sits inside "Northern Ireland"; the longer name is the one meant.
    assert read_place("Belfast, Northern Ireland") == Place("GB", northern_ireland=True)
    assert read_place("Dublin, Ireland") == Place("IE")


def test_a_country_name_inside_another_word_is_not_a_country():
    assert read_place("Indianapolis, IN 46204") is None
    assert read_place("Hollandse Kade 3") is None


@pytest.mark.parametrize("text", ["", "   ", "warehouse 4", "Kingstown, Saint Vincent"])
def test_what_names_no_known_country_reads_as_nothing(text):
    assert read_place(text) is None


# --- Article 4: what a Member State's code does not cover ------------------


@pytest.mark.parametrize("text,country", [
    (picked("Helgoland", "DEHGL", "SH, DE"), "DE"),
    (picked("Ceuta", "ESCEU", "ES"), "ES"),
    (picked("Melilla", "ESMLN", "ML, ES"), "ES"),
    ("Livigno, Italy", "IT"),
    ("Büsingen am Hochrhein, Germany", "DE"),
])
def test_the_places_article_4_takes_out_are_outside(text, country):
    place = read_place(text)
    assert place == Place(country, outside_customs_territory=True)
    assert not place.in_ens_area


def test_the_faroes_and_greenland_are_outside_by_their_own_codes():
    assert not Place("FO").in_ens_area
    assert not Place("GL").in_ens_area
    assert "FO" not in EU_CUSTOMS_TERRITORY and "GL" not in EU_CUSTOMS_TERRITORY


def test_the_canary_islands_and_aland_are_inside():
    assert Place("ES").in_ens_area
    assert read_place("Las Palmas, Spain").in_ens_area
    assert Place("AX").in_ens_area


# --- Northern Ireland ---------------------------------------------------------


@pytest.mark.parametrize("text", [
    picked("Belfast", "GBBEL", "BFS, GB"),
    picked("Larne", "GBLAR", "LRN, GB"),
    picked("Warrenpoint", "GBWPT", "DOW, GB"),
    picked("Londonderry", "GBLDY", "DRY, GB"),
    picked("Kilkeel", "GBKLK", "NMD, GB"),
    picked("Belfast International Airport", "BFS", "Belfast, GB"),
    picked("City of Derry Airport", "LDY", "Derry, Derry and Strabane, GB"),
    "Titanic Quarter, Belfast, Northern Ireland",
    "Belfast, Noord-Ierland",
])
def test_northern_ireland_is_read_as_inside_the_ens_area(text):
    place = read_place(text)
    assert place.country == "GB" and place.northern_ireland
    assert place.in_ens_area


@pytest.mark.parametrize("text", [
    picked("Bangor", "GBBNG", "GWN, GB"),   # the Welsh Bangor, not the Northern Irish one
    picked("Felixstowe", "GBFXT", "SFK, GB"),
    picked("London Heathrow Airport", "LHR", "London, GB"),
    "Manchester, United Kingdom",
])
def test_great_britain_is_outside(text):
    place = read_place(text)
    assert place.country == "GB" and not place.northern_ireland
    assert not place.in_ens_area


# --- the ENS verdict ---------------------------------------------------------


def route(origin: str, destination: str, **more: str) -> dict[str, str]:
    return {"loading_point": origin, "discharge_point": destination, **more}


def test_entering_the_area_from_outside_is_where_the_ens_applies():
    verdict = assess(route("Shanghai, China", picked("Rotterdam", "NLRTM", "ZH, NL")))["ens_mrn"]
    assert (verdict.applies, verdict.reason) == ("yes", "ens_entering")
    assert (verdict.origin, verdict.destination) == ("CN", "NL")


def test_into_norway_or_switzerland_counts_as_entering_the_area():
    assert assess(route("New York, United States", "Oslo, Norway"))["ens_mrn"].reason == "ens_entering"
    assert assess(route("Toronto, Canada", "Basel, Switzerland"))["ens_mrn"].reason == "ens_entering"


def test_great_britain_to_northern_ireland_is_entering():
    verdict = assess(route(picked("Liverpool", "GBLIV", "LIV, GB"), picked("Belfast", "GBBEL", "BFS, GB")))["ens_mrn"]
    assert (verdict.applies, verdict.reason) == ("yes", "ens_entering")


def test_within_the_area_no_ens_is_asked_for():
    for origin, destination in [
        ("Rotterdam, NL", "Berlin, Germany"),
        ("Rotterdam, NL", "Oslo, Norway"),
        ("Basel, Switzerland", "Milano, Italy"),
        ("Dublin, Ireland", "Belfast, Northern Ireland"),
    ]:
        verdict = assess(route(origin, destination))["ens_mrn"]
        assert (verdict.applies, verdict.reason) == ("no", "ens_within_area"), (origin, destination)


def test_leaving_the_area_is_not_entering_it():
    verdict = assess(route("Rotterdam, NL", "New York, United States"))["ens_mrn"]
    assert (verdict.applies, verdict.reason) == ("no", "ens_leaving")


def test_a_route_that_never_touches_the_area_gets_no_ens():
    verdict = assess(route("Shanghai, China", "Los Angeles, United States"))["ens_mrn"]
    assert (verdict.applies, verdict.reason) == ("no", "ens_outside")


def test_a_delivery_in_ceuta_is_not_entering_the_customs_territory():
    verdict = assess(route("Tangier, Morocco", picked("Ceuta", "ESCEU", "ES")))["ens_mrn"]
    assert verdict.reason == "ens_outside"


def test_the_final_destination_outranks_the_discharge_point():
    # Discharged in Rotterdam, delivered in Basel: the goods still enter the area.
    values = route("Shanghai, China", picked("Rotterdam", "NLRTM", "ZH, NL"),
                   final_destination="Basel, Switzerland")
    assert assess(values)["ens_mrn"].destination == "CH"
    # Discharged in Rotterdam, delivered in Manchester: they leave it again,
    # and "entering" is still the verdict for the leg that enters.
    values = route("Shanghai, China", picked("Rotterdam", "NLRTM", "ZH, NL"),
                   final_destination="Manchester, United Kingdom")
    assert assess(values)["ens_mrn"].reason == "ens_outside"


def test_an_unreadable_route_end_is_unknown_not_guessed():
    for values in [route("Shanghai, China", "warehouse 4"), route("", "Rotterdam, NL"), {}]:
        verdict = assess(values)["ens_mrn"]
        assert (verdict.applies, verdict.reason) == ("unknown", "ens_unknown")


# --- the AES verdict ---------------------------------------------------------


def test_an_export_from_the_united_states_is_where_the_itn_applies():
    verdict = assess(route(picked("New York", "USNYC", "NY, US"), "Rotterdam, NL"))["aes_itn"]
    assert (verdict.applies, verdict.reason) == ("yes", "aes_export")


def test_canada_is_exempt_under_30_36():
    verdict = assess(route("Detroit, United States", "Toronto, Canada"))["aes_itn"]
    assert (verdict.applies, verdict.reason) == ("exempt", "aes_canada")


def test_whether_30_36_reaches_puerto_rico_is_not_claimed():
    verdict = assess(route(picked("San Juan", "PRSJU", "PR"), "Toronto, Canada"))["aes_itn"]
    assert (verdict.applies, verdict.reason) == ("unknown", "aes_unresolved")


def test_between_the_mainland_and_puerto_rico_is_filed_both_ways():
    assert assess(route("Miami, United States", picked("San Juan", "PRSJU", "PR")))["aes_itn"].reason == "aes_puerto_rico"
    assert assess(route(picked("San Juan", "PRSJU", "PR"), "Miami, United States"))["aes_itn"].reason == "aes_puerto_rico"


def test_to_the_virgin_islands_is_filed_from_the_mainland_and_from_puerto_rico():
    assert assess(route("Miami, United States", picked("Saint Thomas", "VISTT", "VI")))["aes_itn"].reason == "aes_virgin_islands"
    assert assess(route(picked("San Juan", "PRSJU", "PR"), picked("Saint Thomas", "VISTT", "VI")))["aes_itn"].reason == "aes_virgin_islands"


def test_from_the_virgin_islands_to_the_mainland_is_not_among_the_named_movements():
    verdict = assess(route(picked("Saint Thomas", "VISTT", "VI"), "Miami, United States"))["aes_itn"]
    assert (verdict.applies, verdict.reason) == ("no", "aes_not_named")


def test_a_domestic_movement_and_a_foreign_origin_are_no_export():
    assert assess(route("Chicago, United States", "Dallas, United States"))["aes_itn"].reason == "aes_domestic"
    assert assess(route("Rotterdam, NL", "New York, United States"))["aes_itn"].reason == "aes_not_us"


def test_the_itn_verdict_is_unknown_on_an_unreadable_route_too():
    assert assess(route("New York, United States", "somewhere"))["aes_itn"].applies == "unknown"


# --- the export says it, once, and never refuses -----------------------------


def _document_with_references():
    for key in ("cmr", "bill_of_lading", "sea_waybill"):
        document = get_document(key)
        if document and any(s.get("ref") == "references" for s in document.get("sections", [])):
            return document
    pytest.skip("no document carries the shared references section")


def test_an_applicable_empty_reference_is_a_warning_on_export():
    document = _document_with_references()
    values = route("Shanghai, China", picked("Rotterdam", "NLRTM", "ZH, NL"))
    _, warnings = validate_document(document, values, [], None, "en")
    assert any(w.startswith("ENS reference: on this route") for w in warnings), warnings
    assert not any(w.startswith("AES ITN") for w in warnings)


def test_a_filled_or_inapplicable_reference_is_not_mentioned():
    document = _document_with_references()
    values = route("Shanghai, China", picked("Rotterdam", "NLRTM", "ZH, NL"), ens_mrn="26NLA2345678901234")
    _, warnings = validate_document(document, values, [], None, "en")
    assert not any(w.startswith("ENS reference") for w in warnings)
    values = route("Rotterdam, NL", "Berlin, Germany")
    _, warnings = validate_document(document, values, [], None, "en")
    assert not any(w.startswith("ENS reference") for w in warnings)


def test_the_warning_speaks_the_document_language():
    document = _document_with_references()
    values = route("Shanghai, China", picked("Rotterdam", "NLRTM", "ZH, NL"))
    for lang, opening in [("nl", "ENS-referentie: op deze route"), ("de", "ENS-Referenz: Auf dieser Route"),
                          ("fr", "Référence ENS : sur cet itinéraire")]:
        _, warnings = validate_document(document, values, [], None, lang)
        assert any(w.startswith(opening) for w in warnings), (lang, warnings)


def test_the_warning_never_blocks_the_export():
    document = _document_with_references()
    values = route("Shanghai, China", picked("Rotterdam", "NLRTM", "ZH, NL"))
    errors, _ = validate_document(document, values, [], None, "en")
    assert not any("ENS" in e for e in errors)


# --- the endpoint -------------------------------------------------------------


def _client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="test", role="user", active=True)
    return TestClient(app)


def test_the_endpoint_answers_per_field_with_the_ground():
    try:
        response = _client().post("/api/documents/customs-route", json={
            "values": route(picked("New York", "USNYC", "NY, US"), picked("Rotterdam", "NLRTM", "ZH, NL"))})
        assert response.status_code == 200
        verdicts = response.json()["verdicts"]
        assert verdicts["ens_mrn"] == {
            "field": "ens_mrn", "applies": "yes", "reason": "ens_entering",
            "origin": "US", "destination": "NL"}
        assert verdicts["aes_itn"]["applies"] == "yes"
        assert verdicts["aes_itn"]["reason"] == "aes_export"
    finally:
        app.dependency_overrides.clear()


def test_the_endpoint_wants_an_object_of_values():
    try:
        assert _client().post("/api/documents/customs-route", json={"values": "x"}).status_code == 422
        assert _client().post("/api/documents/customs-route", json={}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_the_endpoint_is_behind_the_login():
    with TestClient(app) as anonymous:
        assert anonymous.post("/api/documents/customs-route", json={"values": {}}).status_code == 401
