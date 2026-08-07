"""Een controle die niet liep, mag er niet uitzien als een controle die slaagde.

Twee gaten, dezelfde vorm. De Q-controle van IATA 5.0.2.11 rekent alleen als de
gebruiker M invult, en dat is onvermijdelijk: CargoPilot heeft de
hoeveelheidstabellen van de DGR niet. Wat wel te vermijden was, is dat het
stilzwijgend gebeurt.

v1.30.0 zei het al op het scherm, maar op twee plekken niet ver genoeg:

- de melding werd in de route berekend, dus de export — waar het document
  daadwerkelijk de deur uit gaat — zei er niets over, terwijl exporter.py er
  zelf bij staat dat het scherm nooit de enige plek mag zijn;
- een positie zonder invoer werd overgeslagen, dus zodra één andere positie wel
  was ingevuld gold de hele zending als "gecontroleerd".
"""

from app.services.dg.compliance import check_compliance
from app.services.documents.exporter import get_document, validate_document

FILLED = [
    {"un_number": "1263", "class": "3", "q_net_quantity": "1", "q_max_net_quantity": "10"},
    {"un_number": "1866", "class": "3", "q_net_quantity": "1", "q_max_net_quantity": "10"},
]
EMPTY = [{"un_number": "1993", "class": "3"}, {"un_number": "1224", "class": "3"}]


def test_a_position_with_two_substances_and_no_input_is_named_not_checked():
    out = check_compliance([{"line_id": "B", "products": EMPTY}], ["IATA_DGR"], "en")
    assert [q["status"] for q in out["q_values"]] == ["not_checked"]


def test_one_unchecked_position_makes_the_whole_shipment_unchecked():
    out = check_compliance(
        [{"line_id": "A", "products": FILLED}, {"line_id": "B", "products": EMPTY}],
        ["IATA_DGR"], "en",
    )
    assert [(q["position"], q["status"]) for q in out["q_values"]] == [
        ("A", "ok"), ("B", "not_checked"),
    ]
    assert out["q_check_status"]["status"] == "not_checked"


def test_a_single_substance_on_a_position_needs_no_q():
    """'All packed in one' vergt meer dan één stof; hier valt niets te melden."""
    out = check_compliance(
        [{"line_id": "A", "products": [EMPTY[0]]}], ["IATA_DGR"], "en"
    )
    assert out["q_values"] == []
    assert out["q_check_status"]["status"] == "not_checked"


def test_a_fully_entered_shipment_reports_checked():
    out = check_compliance([{"line_id": "A", "products": FILLED}], ["IATA_DGR"], "en")
    assert out["q_check_status"]["status"] == "checked"


def test_the_status_belongs_to_the_outcome_not_to_one_endpoint():
    """Iedere aanroeper krijgt hem, ook de export. Dat is het hele punt."""
    out = check_compliance([{"line_id": "A", "products": EMPTY}], ["IATA_DGR"], "en")
    assert "q_check_status" in out


def test_road_does_not_get_an_air_status():
    assert "q_check_status" not in check_compliance(
        [{"line_id": "A", "products": EMPTY}], ["ADR"], "en"
    )


AIR_LINE = [{"line_id": "L1", "products": [
    {"un_number": "1263", "proper_shipping_name": "PAINT", "class": "3",
     "packing_group": "II", "iata_packing_instruction": "353",
     "quantity_packages": "2", "type_of_package": "box",
     "net_quantity_per_package": "5 L", "net_mass_liters_per_package": "5"},
    {"un_number": "1866", "proper_shipping_name": "RESIN SOLUTION", "class": "3",
     "packing_group": "II", "iata_packing_instruction": "353",
     "quantity_packages": "2", "type_of_package": "box",
     "net_quantity_per_package": "5 L", "net_mass_liters_per_package": "5"},
]}]


def test_the_shippers_declaration_says_that_no_q_was_computed():
    _, warnings = validate_document(get_document("iata_dgd"), {}, [], AIR_LINE, "en")
    assert any("5.0.2.11" in warning for warning in warnings)


def test_the_document_stays_quiet_when_the_q_was_actually_computed():
    line = [{"line_id": "L1", "products": [
        dict(AIR_LINE[0]["products"][0], q_net_quantity="1", q_max_net_quantity="10"),
        dict(AIR_LINE[0]["products"][1], q_net_quantity="1", q_max_net_quantity="10"),
    ]}]
    _, warnings = validate_document(get_document("iata_dgd"), {}, [], line, "en")
    assert not any("5.0.2.11" in warning for warning in warnings)
