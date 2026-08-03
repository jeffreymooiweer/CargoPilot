"""De compliance-endpoint moet onbruikbare invoer weigeren, niet omrekenen.

De controle stond op `list[dict]`, dus Pydantic keek er niet naar. Alles wat
binnenkwam ging de rekenlaag in, die er defensief het beste van maakte. Twee
gevallen zijn daarbij gevaarlijk, omdat ze niet uitkomen op een foutmelding maar
op een *gunstiger* uitkomst dan de werkelijkheid:

- Een negatieve hoeveelheid verlaagt het ADR-puntentotaal en kan een vrijstelling
  voorspiegelen die er niet is.
- Een verkeerd gespeld profiel ("IDMG") levert stilzwijgend geen zeevaartcontrole
  op, en het scherm toont dan een schone uitslag zonder dat er iets is nagekeken.

Beide horen HTTP 422 te geven vóórdat er gerekend wordt.
"""

import pytest
from pydantic import ValidationError

from app.schemas.dg_compliance import ComplianceRequest


def request(**product):
    return ComplianceRequest(
        entries=[{"vehicle": "WAGEN-1", "products": [product]}],
        profiles=["ADR"],
    )


def test_a_normal_request_passes_and_keeps_the_class_field_name():
    """"class" kan in Python geen veldnaam zijn, maar de rekenlaag en de
    frontend kennen het veld zo. Het mag onderweg niet hernoemd raken."""
    payload = ComplianceRequest(
        entries=[{
            "vehicle": "WAGEN-1",
            "products": [{
                "un_number": "1203",
                "class": "3",
                "packing_group": "II",
                "transport_category": "2",
                "adr_total_quantity": "20 L",
            }],
        }],
        profiles=["ADR", "IMDG"],
    )
    product = payload.as_dicts()[0]["products"][0]
    assert product["class"] == "3"
    assert product["adr_total_quantity"] == "20 L"
    assert payload.profile_names() == ["ADR", "IMDG"]


def test_an_unknown_profile_is_refused():
    with pytest.raises(ValidationError):
        ComplianceRequest(entries=[], profiles=["IDMG"])


@pytest.mark.parametrize("quantity", ["-5 L", "0", "0 kg", "-0,5"])
def test_a_quantity_that_is_not_positive_is_refused(quantity):
    with pytest.raises(ValidationError) as error:
        request(un_number="1203", adr_total_quantity=quantity)
    assert "groter dan nul" in str(error.value)


def test_a_quantity_without_a_number_is_refused():
    with pytest.raises(ValidationError):
        request(un_number="1203", adr_total_quantity="een paar vaten")


def test_an_empty_quantity_is_allowed_because_the_check_reports_it_itself():
    """Halve invoer is normaal: de wizard stuurt onderweg door en de controle
    hoort 'incomplete' te melden. Weigeren zou het scherm blokkeren."""
    payload = request(un_number="1203", adr_total_quantity="")
    assert payload.entries[0].products[0].un_number == "1203"


def test_an_unknown_packing_group_is_refused():
    with pytest.raises(ValidationError):
        request(un_number="1203", packing_group="IV")


def test_a_packing_group_is_normalised_to_upper_case():
    payload = request(un_number="1203", packing_group="ii")
    assert payload.as_dicts()[0]["products"][0]["packing_group"] == "II"


def test_an_unknown_transport_category_is_refused():
    """ADR 1.1.3.6 kent 0 t/m 4. Een 5 zou geen factor hebben en de positie
    stilzwijgend buiten het puntentotaal laten vallen."""
    with pytest.raises(ValidationError):
        request(un_number="1203", transport_category="5")


def test_a_q_component_of_zero_is_refused_before_it_can_disappear():
    """n of M op nul liet de component uit de Q-som vallen. Nu komt hij er niet
    eens in."""
    with pytest.raises(ValidationError):
        request(un_number="1203", q_net_quantity="5", q_max_net_quantity="0")


def test_fields_the_schema_does_not_name_are_kept():
    """De wizard stuurt meer mee dan de controle leest. Dat mag niet sneuvelen
    op de rand — de rekenlaag en de documenten gebruiken die velden."""
    payload = request(un_number="1203", ems_code="F-E, S-E")
    assert payload.as_dicts()[0]["products"][0]["ems_code"] == "F-E, S-E"
