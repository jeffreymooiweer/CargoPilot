"""What certain classes add to the transport document (5.4.1.2).

Chapter 5.4.1.2 asks for statements that no table can supply: table A says
which substances *may* need temperature control, never what the control
temperature of this consignment is. Until now the application named these in
its guidance panel — "state the control and emergency temperature" — which
tells a consignor about a gap rather than helping them across it, because
there was nowhere to state it.

Each of these is now a field, asked only in the situation its provision
describes and printed in the provision's own words. These tests pin three
properties:

1. the question appears exactly where the provision applies, and nowhere else
   — an ordinary drum of petrol must not grow five new questions;
2. the wording on the document is the regulation's, in the document's
   language;
3. an unanswered field leaves *nothing* on the paper, rather than half a
   sentence. "Control temperature:  °C" on a signed document is worse than
   silence, because it looks answered.
"""
import pytest

from app.core.languages import SUPPORTED
from app.services.dg.autofill import description_line, open_questions_for


def questions(product: dict, profiles=("ADR",), language="nl") -> list[str]:
    return [q["field"] for q in open_questions_for(product, list(profiles), language)]


PEROXIDE = {"un_number": "3111", "class": "5.2",
            "proper_shipping_name": "ORGANIC PEROXIDE TYPE B, LIQUID, "
                                    "TEMPERATURE CONTROLLED"}
PETROL = {"un_number": "1203", "class": "3", "packing_group": "II"}


# --- where the questions appear ----------------------------------------------


def test_temperature_control_is_asked_for_a_controlled_peroxide():
    asked = questions(PEROXIDE)
    assert "control_temperature" in asked
    assert "emergency_temperature" in asked


def test_an_ordinary_load_is_asked_none_of_them():
    """The cost of getting this wrong is paid by every consignment: five extra
    questions on a drum of petrol would make the wizard worse for everybody."""
    asked = questions(PETROL)
    for field in ("control_temperature", "emergency_temperature",
                  "end_of_holding_time", "specific_gas_name",
                  "responsible_person", "firework_classification"):
        assert field not in asked


def test_a_peroxide_without_temperature_control_is_not_asked():
    """Not every organic peroxide needs control — the list says which do, in
    the entry name itself."""
    asked = questions({"un_number": "3105", "class": "5.2",
                       "proper_shipping_name": "ORGANIC PEROXIDE TYPE D, LIQUID"})
    assert "control_temperature" not in asked


def test_class_six_two_is_asked_for_a_responsible_person():
    assert "responsible_person" in questions({"un_number": "2814", "class": "6.2"})


def test_un_1012_is_asked_which_gas():
    """One UN number, four gases — special provision 398."""
    assert "specific_gas_name" in questions({"un_number": "1012", "class": "2"})
    assert "specific_gas_name" not in questions({"un_number": "1978", "class": "2"})


def test_fireworks_are_asked_for_the_classification_reference():
    assert "firework_classification" in questions(
        {"un_number": "0336", "class": "1.4", "classification_code": "1.4G"})
    assert "firework_classification" not in questions(
        {"un_number": "0004", "class": "1.1", "classification_code": "1.1D"})


def test_a_refrigerated_gas_is_asked_for_its_holding_time_only_in_a_tank():
    """5.4.1.2.2 (d) speaks of tank-containers and portable tanks. A cylinder
    has no holding time to end."""
    tank = {"un_number": "1977", "class": "2",
            "proper_shipping_name": "NITROGEN, REFRIGERATED LIQUID",
            "carriage_mode": "portable_tank"}
    assert "end_of_holding_time" in questions(tank)

    packages = dict(tank)
    packages.pop("carriage_mode")
    assert "end_of_holding_time" not in questions(packages)


def test_the_sea_and_air_profiles_do_not_ask_the_land_provisions():
    """5.4.1.2 is the land regimes' chapter; IMDG and IATA have their own."""
    assert "responsible_person" not in questions(
        {"un_number": "2814", "class": "6.2"}, profiles=("IMDG",))


# --- what reaches the document -----------------------------------------------


def test_the_temperatures_reach_the_line_in_the_provisions_own_words():
    line = description_line(
        dict(PEROXIDE, control_temperature="-10", emergency_temperature="-5"),
        "ADR", "en")
    assert "Control temperature: -10 °C Emergency temperature: -5 °C" in line


def test_the_dutch_document_says_it_in_dutch():
    line = description_line(
        dict(PEROXIDE, control_temperature="-10", emergency_temperature="-5"),
        "ADR", "nl")
    assert "Controletemperatuur: -10 °C" in line
    assert "Noodtemperatuur: -5 °C" in line


def test_a_temperature_entered_with_its_unit_does_not_double_it():
    """People type "-10 °C" as readily as "-10", and the provision's sentence
    supplies the unit itself."""
    line = description_line(
        dict(PEROXIDE, control_temperature="-10 °C", emergency_temperature="-5°C"),
        "ADR", "en")
    assert "°C °C" not in line
    assert "Control temperature: -10 °C" in line


def test_one_temperature_alone_puts_nothing_on_the_document():
    """The provision prints one sentence carrying the pair. Half of it is not
    the statement it asks for, and a document that reads "Control temperature:
    -10 °C Emergency temperature:  °C" looks answered when it is not."""
    line = description_line(dict(PEROXIDE, control_temperature="-10"), "ADR", "en")
    assert "Control temperature" not in line
    assert "Emergency temperature" not in line


def test_the_responsible_person_reaches_the_line():
    line = description_line(
        {"un_number": "2814", "class": "6.2",
         "responsible_person": "J. de Vries, +31 6 12345678"}, "ADR", "nl")
    assert "Verantwoordelijke persoon: J. de Vries, +31 6 12345678" in line


def test_the_holding_time_reaches_the_line():
    line = description_line(
        {"un_number": "1977", "class": "2", "carriage_mode": "portable_tank",
         "end_of_holding_time": "31/12/2026"}, "ADR", "en")
    assert "End of holding time: 31/12/2026" in line


def test_the_firework_reference_reaches_the_line():
    line = description_line(
        {"un_number": "0336", "class": "1.4", "classification_code": "1.4G",
         "firework_classification": "NL/BAM1234"}, "ADR", "en")
    assert "firework reference NL/BAM1234" in line


def test_an_unanswered_field_leaves_nothing_behind():
    line = description_line(PETROL, "ADR", "nl")
    for fragment in ("Controletemperatuur", "Einde holdingtijd",
                     "Verantwoordelijke persoon", "Classificatie van vuurwerk"):
        assert fragment not in line


@pytest.mark.parametrize("language", SUPPORTED)
def test_every_mention_exists_in_every_language(language):
    line = description_line(
        dict(PEROXIDE, control_temperature="-10", emergency_temperature="-5"),
        "ADR", language)
    # Whatever the language, the numbers and the unit are there.
    assert "-10" in line and "-5" in line and "°C" in line
