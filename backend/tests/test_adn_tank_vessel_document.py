"""ADN 5.4.1.1.2: the transport document for carriage in tank vessels.

A cargo tank consignment used to get the packages line of 5.4.1.1.1, and the
two are different document entries. 5.4.1.1.2 — read on printed page 349 of the
UNECE English edition — takes its data from table C: (b) the name of column
(2), (c) the data of column (5) with the numbers after the first in brackets,
(d) the packing group, (e) the mass in tonnes. The ADN's own example is
"UN 1203 MOTOR SPIRIT, 3 (N2, CMR, F), II". And under (h), six numbered
remarks of column (20) put information in the transport document; their text
lives in 3.2.3.1 and is not held here, so the document names the remark rather
than guessing at what it asks.
"""
from app.services.dg.autofill import description_line, prepare_entries


def tank_product(un="1203", **extra):
    prepared = prepare_entries(
        [{"line_id": "L1", "products": [
            {"un_number": un, "carriage_mode": "tank", **extra}]}],
        profiles=["ADN"])
    return prepared["entries"][0]["products"][0]


def test_the_line_is_the_provisions_own_example():
    """Column (5) reads 3+N2+CMR+F for petrol: the first number stands, the
    rest go in brackets — not the labels of table A."""
    line = description_line(tank_product(), "ADN", "en")
    assert line.startswith("UN 1203, MOTOR SPIRIT OR GASOLINE OR PETROL, "
                           "3 (N2, CMR, F), II")


def test_the_name_comes_from_table_c_in_the_documents_language():
    assert "BENZINE OF MOTORBRANDSTOF" in description_line(
        tank_product(), "ADN", "nl")
    assert "ESSENCE" in description_line(tank_product(), "ADN", "fr")
    # The ADN is authentic in English and French; a German document gets the
    # English name rather than an invented German one.
    assert "MOTOR SPIRIT" in description_line(tank_product(), "ADN", "de")


def test_the_mass_is_in_tonnes():
    """(e) says tonnes, and a mass in kilograms converts. Litres do not — not
    without a density this application does not presume to apply."""
    line = description_line(
        tank_product(adr_total_quantity="250000 kg"), "ADN", "nl")
    assert line.endswith("250 t")
    in_litres = description_line(
        tank_product(adr_total_quantity="300000 L"), "ADN", "nl")
    assert " t" not in in_litres


def test_no_tunnel_code_and_no_package_count_on_a_tank_vessel():
    """The tunnel code is a road construct and packages are the other chapter:
    neither belongs in this line."""
    line = description_line(
        tank_product(quantity_packages="4", type_of_package="vaten"),
        "ADN", "nl")
    assert "(D/E)" not in line and "vaten" not in line


def test_a_packages_consignment_keeps_the_packages_line():
    prepared = prepare_entries(
        [{"line_id": "L1", "products": [{"un_number": "1203"}]}],
        profiles=["ADN"])
    line = prepared["document_lines"]["ADN"][0]
    assert "3, II" in line and "(N2" not in line


def test_waste_applies_on_the_water_too():
    """5.4.1.1.3 is a special provision of 5.4.1.1, not of the packages line."""
    line = description_line(tank_product(is_waste="yes"), "ADN", "nl")
    assert ", AFVAL BENZINE" in line


def test_a_substance_table_c_does_not_list_falls_back():
    """UN 1090 acetone is in table C; UN 0004 is not. Where the table has no
    row there is no 5.4.1.1.2 line to compose, and the packages description is
    the least-bad line while the admission check refuses the carriage."""
    line = description_line(tank_product("0004"), "ADN", "nl")
    assert "AMMONIUMPIKRAAT" in line


def test_a_document_remark_reaches_the_paper():
    """UN 1131 carbon disulphide carries remark 2 and 31 — neither is a
    document remark. UN 1040 ethylene oxide is not in table C. The measured
    case: find a substance whose column (20) carries one of 3, 17, 22, 39, 42
    or 47 and pin that the export warns for it."""
    import json
    from pathlib import Path

    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document

    seed = json.loads(
        (Path(__file__).resolve().parents[1]
         / "seed" / "dg" / "adn_table_c.json").read_text(encoding="utf-8"))
    import re
    wanted = {"3", "17", "22", "39", "42", "47"}
    carrier = next(
        row for row in seed["entries"]
        if wanted & set(re.findall(r"\d+", str(row.get("remarks") or ""))))

    values = {
        "consignor_name": "Afzender", "consignor_address": "Havenweg 1",
        "consignee_name": "Ontvanger", "consignee_address": "Hafenstrasse 4",
        "loading_point": "Rotterdam", "discharge_point": "Duisburg",
        "established_place": "Rotterdam", "established_date": "2026-08-15",
    }
    goods = [{"line_id": "1", "products": [{
        "un_number": carrier["un"], "carriage_mode": "tank",
        "class": carrier.get("class", "")}]}]
    _errors, warnings = validate_document(
        get_document("adn_transport_doc"), values, [], goods, "nl")
    assert any("5.4.1.1.2 (h)" in w for w in warnings), warnings
