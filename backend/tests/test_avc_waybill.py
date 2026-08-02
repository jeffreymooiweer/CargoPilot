"""Tests voor de AVC-vrachtbrief en de ADR-omschrijving op de CMR.

ADR 5.4.1 schrijft geen vorm voor het vervoersdocument voor: een vrachtbrief
met de omschrijving van 5.4.1.1.1 volstaat. Daarom draagt zowel de CMR als de
AVC-vrachtbrief die omschrijving, en is een apart ADR-wegdocument vervallen.

De AVC-vrachtbrief vult — net als de CMR — het officiële formulier in. Dat
formulier heeft geen AcroForm-velden, dus de waarden komen als tekstlaag over
templates/forms/avc.pdf heen; de tests controleren daarom zowel de tekst als
de positie waarop die tekst terechtkomt.
"""

import fitz
import pytest

from app.services.dg.autofill import prepare_entries
from app.services.documents.avc_form import fill_avc_waybill, has_avc_template
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


def _render(dangerous_goods, lang="nl"):
    """Vul het formulier en lever (volledige tekst, woorden met positie) op."""
    path = fill_avc_waybill(VALUES, LINES, dangerous_goods, lang)
    try:
        page = fitz.open(path)[0]
        return page.get_text(), page.get_text("words")
    finally:
        path.unlink(missing_ok=True)


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


def test_the_official_avc_template_is_shipped():
    """De vrachtbrief vult een bestaand formulier in; die template hoort in de repo."""
    assert has_avc_template()


def test_avc_waybill_fills_the_official_form(prepared):
    text, _words = _render(prepared)

    # De template zelf blijft staan: beide panelen en de AVC-verwijzing.
    assert "VRACHTBRIEF - VERVOERDOCUMENT" in text
    assert "ONTVANGSTBEWIJS" in text
    assert "vervoercondities 2002" in text
    # Onze waarden staan erin, in beide panelen.
    assert text.count("Mooiweer Logistiek BV") == 2
    assert text.count("Bouwbedrijf De Vries") == 2
    assert text.count("Transport Jansen") == 2
    assert "12-BXG-4" in text
    assert "Rotterdam" in text and "2026-08-02" in text
    # Franco aangekruist, niet franco niet: één kruisje per paneel.
    crosses = sorted((round(w[0]), round(w[1])) for w in _words if w[4] == "X")
    assert crosses == [(38, 248), (419, 248)]
    # De gevaarlijke stof staat als ADR-omschrijving in de kolom 'inhoud'.
    assert "UN 1203, GASOLINE, 3, II," in text
    assert "Totale hoeveelheid per vervoerscategorie" in text
    # Totalen over beide regels: 10 + 4 colli, 165 + 820 kg.
    assert text.count("14") >= 2 and text.count("985") >= 2
    # De disclaimer hoort op elk gegenereerd document te staan.
    assert "CONCEPT" in text


def test_avc_values_land_inside_their_boxes(prepared):
    """De overlay is coördinaatgestuurd: verschuift die, dan is het formulier fout."""
    _text, words = _render(prepared)

    def box_of(needle):
        hits = [w for w in words if w[4] == needle]
        assert hits, f"{needle} niet gevonden"
        return hits[0]

    # 'Mooiweer' staat in het afzendervak: onder het label (y > 52) en
    # boven de scheidingslijn op y 110.
    x0, y0, _x1, y1, *_ = box_of("Mooiweer")
    assert 33 < x0 < 121 and 52 < y0 and y1 < 110
    # 'Bouwbedrijf' staat in het afleveradresvak (y 110-228).
    _x0, y0, _x1, y1, *_ = box_of("Bouwbedrijf")
    assert 121 < y0 and y1 < 228
    # De vervoerder staat rechts van de frankeringskolom (x > 120,8).
    x0, y0, _x1, y1, *_ = box_of("Jansen")
    assert x0 > 120.8 and 243 < y0 and y1 < 275

    # Het afzendervak is smaller dan het kader: de kleine-letterkolom begint
    # op x 299,2 en mag niet worden overschreven.
    for x0, _y0, x1, y1, word, *_ in words:
        if x0 < 299 and y1 < 110 and word not in {"niet", "voor", "in", "de"}:
            assert x1 <= 299.2, f"{word} loopt in de kleine-letterkolom"

    # De gewichten staan rechtsuitgelijnd in de gewichtskolom.
    x0, _y0, x1, _y1, *_ = box_of("165")
    assert 350 < x1 <= 391


def test_avc_waybill_without_dangerous_goods():
    text, _words = _render(None)
    assert "jerrycan benzine" in text
    assert "UN 1203" not in text
    assert "vervoerscategorie" not in text


def test_avc_waybill_in_english():
    text, _words = _render(None, "en")
    # De template is Nederlands; alleen onze eigen tekst volgt de taalkeuze.
    assert "DRAFT" in text and "CONCEPT" not in text
    assert "jerrycan benzine" in text


def test_avc_long_description_wraps_inside_the_contents_column(prepared):
    """De kolom 'inhoud' mag niet in de kolom 'gewicht in kg' lopen."""
    _text, words = _render(prepared)
    goods = [w for w in words if 283 < w[1] < 552 and 240 < w[0] < 406]
    assert goods, "geen goederenregels gevonden"
    for _x0, _y0, x1, _y1, word, *_ in goods:
        if word in {"165", "820"}:
            continue
        assert x1 <= 352, f"{word} loopt tot {x1:.1f} en botst met de gewichtskolom"
