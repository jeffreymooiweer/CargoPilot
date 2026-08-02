"""Regression tests for the defects found in the external DG review.

Each test here reproduces a reported failure: quantities that survived an edit,
a Q value that rounded an exceedance away, negative quantities that lowered a
points total, invalid Q components that vanished silently, an ADR packing
instruction on the IATA declaration, and an export that never re-ran the
compliance engine. None of these may come back.
"""

from app.services.dg.autofill import prepare_entries
from app.services.dg.compliance import _num, check_adr_points, check_q_value
from app.services.documents import get_document, validate_document
from app.services.documents.pdf_forms import fill_iata

LINES = [{"line_id": 1, "include": True, "quantity": 2, "unit": "stuks", "description": "x"}]


def entry(**product):
    return [{"line_id": 1, "products": [product]}]


# --- Derived quantities must follow the input, not the first calculation ------

def test_derived_totals_are_recomputed_after_an_edit():
    """2 packages x 10 L, then edited to 3 x 20 L: 60 L, not the stale 20 L."""
    first = prepare_entries(
        entry(un_number="1203", quantity_packages="2", net_mass_liters_per_package="10 L"),
        LINES, ["ADR"], "nl",
    )["entries"][0]["products"][0]
    assert first["adr_total_quantity"] == "20 L"
    assert first["q_net_quantity"] == "10 L"

    edited = {**first, "quantity_packages": "3", "net_mass_liters_per_package": "20 L"}
    second = prepare_entries([{"line_id": 1, "products": [edited]}], LINES, ["ADR"], "nl")
    product = second["entries"][0]["products"][0]
    assert product["adr_total_quantity"] == "60 L"
    assert product["q_net_quantity"] == "20 L"


def test_an_explicit_override_survives_recomputation():
    prepared = prepare_entries(
        entry(un_number="1203", quantity_packages="2", net_mass_liters_per_package="10 L",
              adr_total_quantity_override="15 L"),
        LINES, ["ADR"], "nl",
    )["entries"][0]["products"][0]
    assert prepared["adr_total_quantity"] == "15 L"


# --- The Q value must not round an exceedance away ----------------------------

def test_q_boundary_case_is_exceeded():
    """0.50001 + 0.50001 = 1.00002 -> Q 1.1, exceeded. Rounding the components
    first made this 1.0 and called it fine."""
    result = check_q_value(
        [{"line_id": 1, "products": [
            {"q_net_quantity": "0.50001", "q_max_net_quantity": "1"},
            {"q_net_quantity": "0.50001", "q_max_net_quantity": "1"},
        ]}], "nl",
    )[0]
    assert result["q_value"] == 1.1
    assert result["status"] == "exceeded"
    assert result["exceeded"] is True


def test_a_valid_q_still_passes():
    result = check_q_value(
        [{"line_id": 1, "products": [
            {"q_net_quantity": "2", "q_max_net_quantity": "10"},
            {"q_net_quantity": "3", "q_max_net_quantity": "10"},
        ]}], "nl",
    )[0]
    assert result["q_value"] == 0.5
    assert result["status"] == "ok"


def test_an_invalid_q_component_is_reported_not_dropped():
    """M = 0 used to make the component vanish; now the position says why Q
    cannot be determined."""
    result = check_q_value(
        [{"line_id": 1, "products": [
            {"q_net_quantity": "5", "q_max_net_quantity": "0"},
            {"q_net_quantity": "5", "q_max_net_quantity": "10"},
        ]}], "nl",
    )[0]
    assert result["status"] == "incomplete"
    assert result["q_value"] is None
    assert result["invalid_components"]


def test_a_negative_q_component_cannot_offset_a_real_one():
    result = check_q_value(
        [{"line_id": 1, "products": [
            {"q_net_quantity": "-5", "q_max_net_quantity": "10"},
            {"q_net_quantity": "30", "q_max_net_quantity": "10"},
        ]}], "nl",
    )[0]
    assert result["status"] == "incomplete"


# --- Negative quantities are invalid input, never a lower points total --------

def test_the_number_parser_keeps_the_sign():
    assert _num("-5 L") == -5.0
    assert _num("12,5 L") == 12.5


def test_negative_adr_quantities_do_not_produce_negative_points():
    result = check_adr_points(entry(transport_category="2", adr_total_quantity="-5 L"), "nl")
    assert result["status"] == "incomplete"
    assert result["total_points"] == 0.0

    numeric = check_adr_points(entry(transport_category="2", adr_total_quantity=-5), "nl")
    assert numeric["status"] == "incomplete"


# --- The IATA declaration carries an IATA packing instruction or none ---------

IATA_PRODUCT = {
    "un_number": "1203", "proper_shipping_name": "GASOLINE", "class": "3",
    "packing_group": "II", "quantity_packages": "2", "type_of_package": "fibreboard box",
    "net_mass_liters_per_package": "5 L",
}


def test_the_dgd_prefers_the_iata_packing_instruction():
    block = fill_iata({}, entry(**IATA_PRODUCT, packing_instruction="P001",
                                iata_packing_instruction="353"), "nl")
    assert "353" in block["Nature and Quantity of Dangerous Goods"]
    assert "P001" not in block["Nature and Quantity of Dangerous Goods"]


def test_an_adr_instruction_never_reaches_the_dgd():
    """P001, IBC02 and the like are meaningless in the air; blank is honest."""
    block = fill_iata({}, entry(**IATA_PRODUCT, packing_instruction="P001"), "nl")
    assert "P001" not in block["Nature and Quantity of Dangerous Goods"]


def test_a_numeric_instruction_in_the_generic_field_is_accepted():
    """A user who typed the IATA instruction into the generic field keeps it."""
    block = fill_iata({}, entry(**IATA_PRODUCT, packing_instruction="353"), "nl")
    assert "353" in block["Nature and Quantity of Dangerous Goods"]


def test_the_emergency_contact_reaches_the_pdf():
    fields = fill_iata(
        {"handling_information": "Keep cool", "emergency_contact": "+31 6 12345678"},
        entry(**IATA_PRODUCT), "nl",
    )
    assert "+31 6 12345678" in fields["Additional Handling Information"]
    assert "Keep cool" in fields["Additional Handling Information"]


# --- Export re-runs the compliance engine server-side -------------------------

VALUES = {
    "consignor_name": "A", "consignor_address": "a", "consignee_name": "B",
    "consignee_address": "b", "loading_point": "AMS", "discharge_point": "JFK",
    "aircraft_limitation": "cargo", "shipment_type": "non-radioactive",
    "emergency_contact": "+31 6 1", "signatory_name": "S", "declaration_place": "AMS",
    "declaration_date": "2026-08-02", "shipment_reference": "r",
}


def test_an_exceeded_q_blocks_the_export():
    doc = get_document("iata_dgd")
    dg = [{"line_id": 1, "products": [
        {**IATA_PRODUCT, "iata_packing_instruction": "353",
         "q_net_quantity": "0.50001", "q_max_net_quantity": "1"},
        {**IATA_PRODUCT, "un_number": "1263", "proper_shipping_name": "PAINT",
         "iata_packing_instruction": "353", "packing_instruction": "353",
         "q_net_quantity": "0.50001", "q_max_net_quantity": "1"},
    ]}]
    dg[0]["products"][0]["packing_instruction"] = "353"
    errors, _warnings = validate_document(doc, VALUES, [], dg, "nl")
    assert any("Q = 1.1" in e for e in errors)


def test_a_segregation_error_blocks_the_export():
    """Loose lithium batteries next to a flammable liquid may not fly."""
    doc = get_document("iata_dgd")
    dg = [{"line_id": 1, "products": [
        {"un_number": "3480", "proper_shipping_name": "LITHIUM ION BATTERIES",
         "class": "9", "packing_instruction": "965", "quantity_packages": "1",
         "type_of_package": "box", "net_mass_liters_per_package": "5 kg"},
        {**IATA_PRODUCT, "packing_instruction": "353"},
    ]}]
    errors, _warnings = validate_document(doc, VALUES, [], dg, "nl")
    assert any("9.3.2" in e for e in errors)


def test_a_clean_shipment_still_exports():
    doc = get_document("iata_dgd")
    dg = [{"line_id": 1, "products": [{**IATA_PRODUCT, "packing_instruction": "353"}]}]
    errors, _warnings = validate_document(doc, VALUES, [], dg, "nl")
    assert errors == []
