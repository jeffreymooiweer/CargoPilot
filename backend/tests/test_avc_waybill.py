"""Tests voor de AVC-vrachtbrief en de ADR-omschrijving op de CMR.

ADR 5.4.1 schrijft geen vorm voor het vervoersdocument voor: een vrachtbrief
met de omschrijving van 5.4.1.1.1 volstaat. Daarom draagt zowel de CMR als de
AVC-vrachtbrief die omschrijving, en is een apart ADR-wegdocument vervallen.
"""

import fitz
import pytest

from app.services.dg.autofill import prepare_entries
from app.services.documents.avc_render import render_avc_waybill
from app.services.documents.pdf_forms import fill_cmr
from app.services.documents.registry import get_document, get_registry

LINES = [
    {
        "line_id": 1, "include": True, "quantity": 10, "unit": "jerrycan",
        "weight_total_kg": 165, "transport_volume_m3": 0.3, "description": "jerrycan benzine",
    },
    {
        "line_id": 2, "include": True, "quantity": 4, "unit": "pallet",
        "weight_total_kg": 820, "description": "pallets kalkzandsteen",
    },
]
ENTRIES = [{
    "line_id": 1, "vehicle": "Jerrycans",
    "products": [{"un_number": "1203", "net_mass_liters_per_package": "20 L"}],
}]
VALUES = {
    "consignor_name": "Mooiweer Logistiek BV",
    "consignor_address": "Havenweg 12\n3011 AA Rotterdam",
    "consignee_name": "Bouwbedrijf De Vries",
    "consignee_address": "Industrieplein 5\n7511 JK Enschede",
    "carrier_name": "Transport Jansen",
    "freight_payment": "franco",
    "vehicle_registration": "12-BXG-4",
    "loading_point": "Rotterdam",
    "loading_date": "2026-08-02",
}


@pytest.fixture
def prepared():
    return prepare_entries(ENTRIES, LINES, ["ADR"], "nl")["entries"]


def test_adr_road_document_is_replaced_by_the_avc_waybill():
    """Het losse ADR-wegdocument is vervallen; de AVC-vrachtbrief staat ervoor in de plaats."""
    registry = get_registry()
    keys = [doc["key"] for doc in registry["documents"]]
    assert "adr_transport_doc" not in keys
    assert "avc_waybill" in keys

    road = next(m for m in registry["modalities"] if m["key"] == "road")
    assert "avc_waybill" in road["documents"]
    # Binnenvaart houdt wel een eigen ADN-document: daar is geen vrachtbrief.
    assert "adn_transport_doc" in keys

    avc = get_document("avc_waybill")
    assert avc["dg_profile"] == "ADR"
    # Geen dg_only: de vrachtbrief is er ook voor zendingen zonder gevaarlijke stoffen.
    assert not avc.get("dg_only")


def test_cmr_carries_the_adr_description_and_category_totals(prepared):
    """Zonder de 5.4.1.1.1-regel zou de CMR niet als vervoersdocument volstaan."""
    fields = fill_cmr({**VALUES, "sender_instructions": "Voorzichtig laden"}, LINES, prepared, "nl")

    assert fields["VakRood06Regel01Kolom06"] == "UN 1203, GASOLINE, 3, II, (D/E), 10 jerrycan, 200 L"
    # Regels zonder gevaarlijke stoffen houden hun gewone omschrijving.
    assert fields["VakRood06Regel02Kolom06"] == "4 × pallets kalkzandsteen"
    # De massa wordt niet dubbel geteld over de DG-regels.
    assert fields["VakRood06Regel01Kolom11"] == "165"

    # Vak 13: instructie van de afzender plus het totaal per vervoerscategorie.
    assert "Voorzichtig laden" in fields["VakRood13"]
    assert "Totale hoeveelheid per vervoerscategorie: 2: 200 L" in fields["VakRood13"]


def test_cmr_without_dangerous_goods_keeps_plain_descriptions():
    fields = fill_cmr(VALUES, LINES, None, "nl")
    assert fields["VakRood06Regel01Kolom06"] == "10 × jerrycan benzine"
    assert "VakRood13" not in fields


def test_avc_waybill_renders_both_panels_and_the_avc_clause(prepared):
    path = render_avc_waybill(get_document("avc_waybill"), VALUES, LINES, prepared, "nl")
    try:
        pdf = fitz.open(path)
        assert pdf.page_count == 1
        text = pdf[0].get_text()
    finally:
        path.unlink(missing_ok=True)

    # Beide panelen van het formulier.
    assert "VRACHTBRIEF" in text
    assert "ONTVANGSTBEWIJS" in text
    # De verwijzingsclausule maakt de AVC 2002 van toepassing.
    assert "Algemene Vervoercondities 2002" in text
    assert "Stichting Vervoeradres" in text
    # Partijen, vervoerder en frankering.
    assert "Mooiweer Logistiek BV" in text
    assert "Bouwbedrijf De Vries" in text
    assert "Transport Jansen" in text
    assert "[X] Franco" in text
    # De gevaarlijke stof staat als ADR-omschrijving in de kolom 'inhoud'.
    assert "UN 1203, GASOLINE, 3, II, (D/E)" in text
    assert "Totale hoeveelheid per vervoerscategorie" in text
    # Totalen over beide regels: 10 + 4 colli, 165 + 820 kg.
    assert "14" in text and "985" in text
    # De disclaimer hoort op elk gegenereerd document te staan.
    assert "concept" in text


def test_avc_waybill_without_dangerous_goods(prepared):
    path = render_avc_waybill(get_document("avc_waybill"), VALUES, LINES, None, "nl")
    try:
        text = fitz.open(path)[0].get_text()
    finally:
        path.unlink(missing_ok=True)
    assert "jerrycan benzine" in text
    assert "UN 1203" not in text
    assert "vervoerscategorie" not in text


def test_avc_waybill_in_english():
    path = render_avc_waybill(get_document("avc_waybill"), VALUES, LINES, None, "en")
    try:
        text = fitz.open(path)[0].get_text()
    finally:
        path.unlink(missing_ok=True)
    assert "WAYBILL" in text and "RECEIPT" in text
    assert "General Transport Conditions 2002" in text
