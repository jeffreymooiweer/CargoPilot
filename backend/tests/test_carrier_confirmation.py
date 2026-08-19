"""Reading a booking confirmation, and the customs references that get a home.

Two roadmap items land together because they meet in the same screen: the
references section gains the ENS (ICS2) and AES ITN fields with their formats
enforced, and a pasted booking confirmation fills the carrier-assigned fields
so nobody retypes what the carrier already sent.

The extractions are formats, not guesses — the AWB check digit (serial mod 7)
is verified, so a phone number is refused six times out of seven; the MRN and
ITN shapes are distinctive at their full length; a booking reference is only
read where the text itself names it one. What the text does not carry is
absent from the answer, never invented.
"""
import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.main import app
from app.core.deps import get_current_user
from app.services.documents import get_document, get_registry, validate_document
from app.services.documents.carrier_confirmation import parse_carrier_confirmation


# --- the parser ---------------------------------------------------------------


def test_an_awb_number_with_its_check_digit_is_read():
    """1234567 mod 7 is 5, so 057-12345675 is a real AWB number."""
    text = "We confirm your booking. AWB: 057-12345675, flight KL0801."
    found = parse_carrier_confirmation(text)
    assert found["awb_number"] == "057-12345675"


def test_a_failed_check_digit_is_no_awb_number():
    found = parse_carrier_confirmation("Call us at 057-12345678 for details.")
    assert "awb_number" not in found


def test_the_awb_survives_spacing_variants():
    for variant in ("05712345675", "057 12345675", "057-12345675"):
        found = parse_carrier_confirmation(f"Air waybill {variant} issued.")
        assert found.get("awb_number") == "057-12345675", variant


def test_a_named_booking_reference_is_read():
    found = parse_carrier_confirmation("Booking reference: NLRTM260819-42 confirmed.")
    assert found["booking_number"] == "NLRTM260819-42"


def test_the_dutch_wording_works_too():
    found = parse_carrier_confirmation("Uw boekingsnummer: ABC12345.")
    assert found["booking_number"] == "ABC12345"


def test_an_unnamed_token_is_not_a_booking_reference():
    """No 'booking' wording, no booking reference — a bare code could be
    anything, and inventing is worse than leaving the field for the user."""
    found = parse_carrier_confirmation("Reference QX99881 assigned to your file.")
    assert "booking_number" not in found


def test_a_booking_line_carrying_the_awb_is_not_doubled():
    found = parse_carrier_confirmation("Booking no: 05712345675 (air waybill).")
    assert found["awb_number"] == "057-12345675"
    assert "booking_number" not in found


def test_an_ens_mrn_is_read_at_its_full_length():
    found = parse_carrier_confirmation("ENS accepted, MRN 26NLA2345678901234.")
    assert found["ens_mrn"] == "26NLA2345678901234"


def test_an_aes_itn_is_read():
    found = parse_carrier_confirmation("EEI filed. ITN: X20260819123456.")
    assert found["aes_itn"] == "X20260819123456"


def test_what_the_text_does_not_carry_is_absent():
    assert parse_carrier_confirmation("") == {}
    assert parse_carrier_confirmation("Thanks for your booking!") == {}


def test_a_whole_confirmation_reads_all_at_once():
    text = """Dear customer,

    Your booking BKG-88231-A is confirmed.
    Air waybill: 074-98765432? no - AWB 074 9876543 5.
    ENS lodged in ICS2 under MRN 26DEB7654321098765.
    """
    found = parse_carrier_confirmation(text)
    assert found["booking_number"] == "BKG-88231-A"
    # 9876543 mod 7 is 5: the second candidate is the real number, the
    # mistyped first one fails its own check digit and is passed over.
    assert found["awb_number"] == "074-98765435"
    assert found["ens_mrn"] == "26DEB7654321098765"


# --- the fields those references live in ---------------------------------------


def references_fields() -> dict:
    section = next(s for s in get_registry()["shared_sections"] if s["key"] == "references")
    return {f["key"]: f for f in section["fields"]}


def test_the_customs_reference_fields_exist_with_their_formats():
    fields = references_fields()
    for key, pattern in (("ens_mrn", r"\d{2}[A-Z]{2}[A-Z0-9]{13}\d"), ("aes_itn", r"X\d{14}")):
        field = fields[key]
        assert field["status"] == "CONDITIONAL"
        assert field["pattern"] == pattern
        for language in ("nl", "en", "de", "fr"):
            assert field["help"][language]
            assert field["format_hint"][language]


def test_a_malformed_itn_blocks_the_export_with_the_format():
    """The pattern mechanism does the enforcing: X123 is not an ITN."""
    document = get_document("cmr")
    errors, _ = validate_document(document, {"aes_itn": "X123"}, [], None, "en")
    assert any("ITN" in error for error in errors)
    errors, _ = validate_document(document, {"aes_itn": "X20260819123456"}, [], None, "en")
    assert not any("ITN" in error for error in errors)


# --- the endpoint ---------------------------------------------------------------


def _client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="test", role="user", active=True)
    return TestClient(app)


def test_the_endpoint_reads_and_stores_nothing():
    try:
        response = _client().post(
            "/api/documents/carrier-confirmation",
            json={"text": "Booking ref: XYZ98765, AWB 057-12345675"})
        assert response.status_code == 200
        found = response.json()["found"]
        assert found == {"awb_number": "057-12345675", "booking_number": "XYZ98765"}
    finally:
        app.dependency_overrides.clear()


def test_an_oversized_paste_is_refused():
    try:
        response = _client().post(
            "/api/documents/carrier-confirmation", json={"text": "x" * 100_001})
        assert response.status_code == 413
    finally:
        app.dependency_overrides.clear()


def test_the_reader_is_behind_the_login():
    with TestClient(app) as anonymous:
        assert anonymous.post(
            "/api/documents/carrier-confirmation", json={"text": "hi"}).status_code == 401
