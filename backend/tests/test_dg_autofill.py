"""Tests voor automatische invulling en modaliteitsverrijking van DG-gegevens."""

from app.services.dg.autofill import adr_category_totals, description_line, prepare_entries
from app.services.dg.compliance import check_imdg_segregation, get_compliance_rules
from app.services.dg.enrichment import describe_excepted_quantity, enrich_un_entry, parse_hazards


def test_parse_hazards_separates_classification_code_from_subsidiary_risks():
    """De classificatiecode (F1) is geen nevengevaar — dat waren de etiketten."""
    petrol = parse_hazards({"class": "3", "classification_code": "F1", "labels": "3"})
    assert petrol["division"] == "3"
    assert petrol["subsidiary_risks"] == []
    assert petrol["classification_code"] == "F1"

    nitric = parse_hazards({"class": "8", "classification_code": "CO1", "labels": "8+5.1"})
    assert nitric["division"] == "8"
    assert nitric["subsidiary_risks"] == ["5.1"]


def test_parse_hazards_resolves_division_for_gases_and_explosives():
    """Tabel A geeft bij gassen alleen '2' en bij explosieven alleen '1'."""
    lpg = parse_hazards({"class": "2", "classification_code": "2F", "labels": "2.1"})
    assert lpg["division"] == "2.1"

    fireworks = parse_hazards({"class": "1", "classification_code": "1.4G", "labels": "1.4"})
    assert fireworks["division"] == "1.4G"

    lithium = parse_hazards({"class": "9", "classification_code": "M4", "labels": "9A"})
    assert lithium["division"] == "9"
    assert lithium["subsidiary_risks"] == []


def test_enrichment_provides_ems_and_air_rules():
    petrol = enrich_un_entry({"un": "1203", "class": "3", "excepted_quantity": "E2", "limited_quantity": "1 L"})
    assert petrol["ems_code"] == "F-E, S-E"
    assert petrol["ems_source"] == "imdg_dgl"
    assert "30 g/ml" in petrol["excepted_quantity_text"]

    lithium = enrich_un_entry({"un": "3480", "class": "9", "excepted_quantity": "E0"})
    assert lithium["cargo_aircraft_only"] is True
    assert lithium["iata_packing_instruction"] == "965"

    toxic_gas = enrich_un_entry({"un": "1017", "class": "2.3"})
    assert toxic_gas["air_forbidden"] is True


def test_excepted_quantity_limits_match_adr_3_5_1_2():
    assert "30 g/ml per binnenverpakking" in describe_excepted_quantity("E1", "nl")
    assert "1000 g/ml per buitenverpakking" in describe_excepted_quantity("E1", "nl")
    assert "300 g/ml per outer packaging" in describe_excepted_quantity("E5", "en")
    assert describe_excepted_quantity("E0", "nl").startswith("E0: niet toegestaan")
    assert describe_excepted_quantity("", "nl") is None


def test_prepare_fills_classification_and_quantities_from_lines():
    entries = [{
        "line_id": 1,
        "vehicle": "Jerrycans",
        "products": [{"un_number": "1203", "net_mass_liters_per_package": "20 L"}],
    }]
    lines = [{"line_id": 1, "quantity": 10, "unit": "jerrycan", "weight_each_kg": 16.5}]

    result = prepare_entries(entries, lines, ["ADR"], "nl")
    product = result["entries"][0]["products"][0]

    assert product["proper_shipping_name"].startswith("GASOLINE")
    assert product["class"] == "3"
    assert product["packing_group"] == "II"
    assert product["transport_category"] == "2"
    assert product["tunnel_code"] == "D/E"
    assert product["quantity_packages"] == "10"
    assert product["type_of_package"] == "jerrycan"
    # 10 colli × 20 L = 200 L, automatisch voor de 1.1.3.6-punten
    assert product["adr_total_quantity"] == "200 L"


def test_prepare_never_overwrites_manual_input():
    entries = [{
        "line_id": 1,
        "vehicle": "Handmatig",
        "products": [{
            "un_number": "1203",
            "proper_shipping_name": "BENZINE (eigen omschrijving)",
            "quantity_packages": "3",
        }],
    }]
    lines = [{"line_id": 1, "quantity": 99, "unit": "vat", "weight_each_kg": 1}]

    product = prepare_entries(entries, lines, ["ADR"], "nl")["entries"][0]["products"][0]
    assert product["proper_shipping_name"] == "BENZINE (eigen omschrijving)"
    assert product["quantity_packages"] == "3"


def test_description_line_follows_adr_5_4_1_1_1():
    product = {
        "un_number": "1203",
        "proper_shipping_name": "BENZINE",
        "class": "3",
        "packing_group": "II",
        "tunnel_code": "D/E",
        "quantity_packages": "10",
        "type_of_package": "jerrycan",
        "net_mass_liters_per_package": "20 L",
    }
    assert description_line(product, "ADR") == "UN 1203, BENZINE, 3, II, (D/E), 10 jerrycan, 200 L"


def test_description_line_adds_imdg_and_iata_specifics():
    product = {
        "un_number": "3480",
        "proper_shipping_name": "LITHIUM ION BATTERIES",
        "class": "9",
        "ems_code": "F-A, S-I",
        "marine_pollutant": "P",
        "cargo_aircraft_only": "Y",
        "iata_packing_instruction": "965",
        "quantity_packages": "2",
        "type_of_package": "doos",
        "net_mass_liters_per_package": "5 kg",
    }
    imdg = description_line(product, "IMDG")
    assert "MARINE POLLUTANT" in imdg and "EmS F-A, S-I" in imdg

    iata = description_line(product, "IATA_DGR")
    assert "PI 965" in iata and "CARGO AIRCRAFT ONLY" in iata
    # De ADR-verpakkingsinstructie hoort niet op een luchtvrachtdocument.
    assert "P001" not in iata


def test_adr_category_totals_group_per_transport_category():
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            {"transport_category": "2", "quantity_packages": "10", "net_mass_liters_per_package": "20 L"},
            {"transport_category": "2", "quantity_packages": "2", "net_mass_liters_per_package": "5 L"},
            {"transport_category": "1", "quantity_packages": "4", "net_mass_liters_per_package": "25 kg"},
        ],
    }]
    totals = adr_category_totals(entries, "nl")
    rows = {row["transport_category"]: row["total"] for row in totals["categories"]}
    assert rows["2"] == "210 L"
    assert rows["1"] == "100 kg"
    assert "Totale hoeveelheid per vervoerscategorie" in totals["statement"]


def test_imdg_segregation_table_is_symmetric_and_complete():
    rules = get_compliance_rules()["imdg_segregation"]
    order = rules["class_order"]
    table = rules["table"]
    assert set(table) == set(order)
    for row in order:
        assert len(table[row]) == len(order)
        for index, column in enumerate(order):
            assert table[row][index] == table[column][order.index(row)], f"{row}×{column}"


def test_imdg_segregation_warns_for_incompatible_classes():
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            {"un_number": "1203", "proper_shipping_name": "BENZINE", "class": "3"},
            {"un_number": "2031", "proper_shipping_name": "SALPETERZUUR", "class": "8", "subsidiary_risks": "5.1"},
        ],
    }]
    warnings = check_imdg_segregation(entries, "nl")
    assert len(warnings) == 1
    # Klasse 3 × 5.1 = code 2 ("separated from"); nevengevaar telt mee.
    assert warnings[0]["code"] == "2"
    assert "Gescheiden van" in warnings[0]["message"]


def test_imdg_segregation_silent_for_compatible_classes():
    entries = [{
        "line_id": 1,
        "vehicle": "Mix",
        "products": [
            {"un_number": "1203", "class": "3"},
            {"un_number": "1830", "class": "8"},
        ],
    }]
    # 3 × 8 = X in de tabel: geen algemene scheiding voorgeschreven.
    assert check_imdg_segregation(entries, "nl") == []


def test_prepare_lists_class_specific_document_requirements():
    entries = [{
        "line_id": 1,
        "vehicle": "Radioactief",
        "products": [{"un_number": "2915"}],
    }]
    requirements = prepare_entries(entries, [], ["ADR", "IATA_DGR"], "nl")["requirements"]
    assert any("transportindex" in item for item in requirements)
    assert any("Shipper's Declaration" in item for item in requirements)
