"""Wat er werkelijk in het geëxporteerde document staat, teruggelezen uit de PDF.

De wizard controleert, maar het scherm mag nooit de enige plek zijn waar dat
gebeurt: een verouderd of nooit ververst schermresultaat mag geen document
opleveren. Deze tests gaan daarom langs de exportkant en lezen de uitkomst terug
uit het bestand dat een gebruiker in handen krijgt — niet uit een tussenlaag.

Twee dingen worden hier vastgelegd die met een unittest niet te vangen zijn:

- de export voert de nalevingscontrole zelf opnieuw uit, met de invoer die op
  dat moment wordt meegestuurd;
- de luchtvaartverklaring draagt de IATA-verpakkingsinstructie en niet de
  ADR-instructie van dezelfde stof. Die twee lijken op elkaar (P001 tegenover
  965) en verwisselen betekent een verklaring die niet klopt met de verpakking.
"""

import pytest
from pypdf import PdfReader

from app.services.documents.exporter import validate_document
from app.services.documents.pdf_forms import fill_pdf_document
from app.services.documents.registry import get_document
from tests.test_documents import BASE_VALUES, LINES, _pdf_visible_text


def air_values(**overrides):
    return dict(
        BASE_VALUES,
        awb_number="020-12345675",
        aircraft_limitation="cargo_only",
        shipment_type="non_radioactive",
        signatory_name="J. Jansen",
        declaration_place="Utrecht",
        declaration_date="2026-07-12",
        emergency_contact="+31 6 12345678",
        **overrides,
    )


def air_entry(**product):
    base = {
        "un_number": "3480",
        "proper_shipping_name": "Lithium ion batteries",
        "class": "9",
        "packing_group": "II",
        "packing_instruction": "965",
        "quantity_packages": "2",
        "type_of_package": "4G box",
        "net_mass_liters_per_package": "5 kg",
    }
    return [{"line_id": 1, "vehicle": "Batterijen", "products": [{**base, **product}]}]


# --- De export controleert zelf ------------------------------------------------

def test_the_export_runs_the_compliance_check_itself():
    """Klasse 1 samen met een andere klasse is verboden onder ADR 7.5.2.1. Dat
    hoort de export tegen te houden, ook als het scherm nooit is ververst."""
    entries = [{
        "line_id": 1,
        "vehicle": "WAGEN-1",
        "products": [
            {"un_number": "0004", "class": "1.1D", "proper_shipping_name": "AMMONIUMPIKRAAT",
             "quantity_packages": "1", "transport_category": "1", "adr_total_quantity": "5 kg"},
            {"un_number": "1203", "class": "3", "proper_shipping_name": "BENZINE",
             "packing_group": "II", "quantity_packages": "1",
             "transport_category": "2", "adr_total_quantity": "20 L"},
        ],
    }]
    errors, _ = validate_document(get_document("cmr"), BASE_VALUES, LINES, entries, "ADR")
    assert any("7.5.2.1" in e for e in errors), errors


def test_a_q_value_above_one_blocks_the_export():
    """IATA 5.0.2.11: boven Q = 1 mag de combinatie zo niet vliegen."""
    entries = [{
        "line_id": 1,
        "vehicle": "COLLO-1",
        "products": [
            {"un_number": "1263", "class": "3", "proper_shipping_name": "VERF",
             "packing_group": "II", "quantity_packages": "1",
             "q_net_quantity": "4", "q_max_net_quantity": "5"},
            {"un_number": "1866", "class": "3", "proper_shipping_name": "HARSOPLOSSING",
             "packing_group": "II", "quantity_packages": "1",
             "q_net_quantity": "3", "q_max_net_quantity": "5"},
        ],
    }]
    errors, _ = validate_document(get_document("iata_dgd"), air_values(), LINES, entries, "IATA")
    assert any("5.0.2.11" in e for e in errors), errors


def test_a_q_value_within_the_limit_does_not_block_the_export():
    entries = [{
        "line_id": 1,
        "vehicle": "COLLO-1",
        "products": [
            {"un_number": "1263", "class": "3", "proper_shipping_name": "VERF",
             "packing_group": "II", "quantity_packages": "1",
             "packing_instruction": "353",
             "q_net_quantity": "1", "q_max_net_quantity": "5"},
            {"un_number": "1866", "class": "3", "proper_shipping_name": "HARSOPLOSSING",
             "packing_group": "II", "quantity_packages": "1",
             "packing_instruction": "353",
             "q_net_quantity": "1", "q_max_net_quantity": "5"},
        ],
    }]
    errors, _ = validate_document(get_document("iata_dgd"), air_values(), LINES, entries, "IATA")
    assert not any("5.0.2.11" in e for e in errors), errors


def test_the_check_uses_the_quantities_that_are_sent_now():
    """Twee keer dezelfde stof, alleen de hoeveelheid verschilt: de uitkomst
    moet meebewegen. Een gecachete uitslag zou hier hetzelfde antwoord geven."""
    def points_for(quantity: str):
        entries = [{
            "line_id": 1, "vehicle": "WAGEN-1",
            "products": [{
                "un_number": "1203", "class": "3", "proper_shipping_name": "BENZINE",
                "packing_group": "II", "quantity_packages": "1",
                "transport_category": "2", "adr_total_quantity": quantity,
            }],
        }]
        return validate_document(get_document("cmr"), BASE_VALUES, LINES, entries, "ADR")

    small_errors, small_warnings = points_for("20 L")
    large_errors, large_warnings = points_for("2000 L")
    # 2000 L in categorie 2 telt voor 6000 punten en gaat ruim over de 1000 heen;
    # 20 L blijft er ver onder. De uitkomsten mogen dus niet gelijk zijn.
    assert (small_errors, small_warnings) != (large_errors, large_warnings)


# --- Wat er in de luchtvaartverklaring terechtkomt ------------------------------

def test_the_air_declaration_carries_the_iata_packing_instruction():
    """P001 is de ADR-instructie voor dezelfde stof; op een DGD hoort 353.

    Ze staan allebei op de stof en verwisselen levert een verklaring op die
    niet klopt met de verpakking die eronder zit.
    """
    entries = air_entry(
        un_number="1263", proper_shipping_name="PAINT", **{"class": "3"},
        packing_instruction="353",          # IATA
        adr_packing_instruction="P001",     # ADR, hoort er niet op
    )
    path = fill_pdf_document("iata_dgd", air_values(), LINES, entries, "en")
    try:
        visible = _pdf_visible_text(path)
        assert "353" in visible
        assert "P001" not in visible
    finally:
        path.unlink(missing_ok=True)


def test_the_authorization_reaches_the_document():
    """Onder welke goedkeuring of vrijstelling de zending mag vliegen.

    De template die CargoPilot invult heeft daar geen apart invulveld voor —
    het Authorization-vak van de DGD zit in de tabel met de goederen — dus het
    komt als eigen benoemde regel onder die tabel. Weglaten kan niet: zonder
    die verwijzing is een zending die er een nodig heeft niet aan te bieden.
    """
    values = air_values(authorization="Competent authority approval NL-2026-0042")
    path = fill_pdf_document("iata_dgd", values, LINES, air_entry(), "en")
    try:
        visible = _pdf_visible_text(path)
        assert "Authorization" in visible
        assert "NL-2026-0042" in visible
    finally:
        path.unlink(missing_ok=True)


def test_without_an_authorization_the_line_is_left_off():
    """Een leeg vak met alleen het woord 'Authorization' erin suggereert dat
    er iets is goedgekeurd."""
    path = fill_pdf_document("iata_dgd", air_values(), LINES, air_entry(), "en")
    try:
        assert "Authorization" not in _pdf_visible_text(path)
    finally:
        path.unlink(missing_ok=True)


def test_the_emergency_contact_reaches_the_document():
    path = fill_pdf_document("iata_dgd", air_values(), LINES, air_entry(), "en")
    try:
        assert "+31 6 12345678" in _pdf_visible_text(path)
    finally:
        path.unlink(missing_ok=True)


def test_the_declaration_is_flat_so_the_values_cannot_be_edited_away():
    """Een ingevuld formulier dat nog bewerkbaar is, is geen verklaring."""
    path = fill_pdf_document("iata_dgd", air_values(), LINES, air_entry(), "en")
    try:
        assert PdfReader(str(path)).get_fields() in (None, {})
    finally:
        path.unlink(missing_ok=True)


# --- IMDG: één eindconclusie ---------------------------------------------------

def test_a_16b_provision_and_the_class_table_resolve_to_one_outcome():
    """7.2.3.1 laat kolom 16b vóórgaan op de scheidingstabel van 7.2.4.

    Waar beide iets zeggen mag er niet één uitkomst blijven staan die de
    andere tegenspreekt: de zwaarste regel regeert en de rest wordt als
    achtergrond gemarkeerd, niet als los tegengesteld advies.
    """
    from app.services.dg.compliance import check_imdg_segregation

    entries = [{
        "line_id": 1, "vehicle": "CONTAINER-1",
        "products": [
            {"un_number": "1203", "class": "3", "proper_shipping_name": "BENZINE",
             "packing_group": "II", "quantity_packages": "1"},
            {"un_number": "1830", "class": "8", "proper_shipping_name": "ZWAVELZUUR",
             "packing_group": "II", "quantity_packages": "1"},
        ],
    }]
    findings = check_imdg_segregation(entries, "nl")
    governing = [f for f in findings if f.get("takes_precedence_over")]
    superseded = [f for f in findings if f.get("superseded_by")]
    # Als er iets voorrang krijgt, moet het overruled deel dat ook zeggen —
    # anders staan er twee gelijkwaardige, tegengestelde uitspraken.
    if governing:
        assert superseded, findings
        for finding in superseded:
            assert finding["severity"] == "info"


@pytest.mark.parametrize("profile", ["ADR", "IMDG", "IATA"])
def test_an_export_without_dangerous_goods_is_not_blocked_by_the_dg_check(profile):
    """De controle mag niets tegenhouden wat geen gevaarlijke stof bevat."""
    document = get_document("cmr" if profile != "IATA" else "iata_dgd")
    errors, _ = validate_document(document, BASE_VALUES, LINES, [], profile)
    assert not any("7.5.2" in e or "5.0.2.11" in e for e in errors), errors
