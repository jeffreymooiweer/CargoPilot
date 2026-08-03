"""Een veld dat een vorm belooft, moet die vorm ook hebben.

De export controleerde tot nu toe alleen of een verplicht veld gevuld was. De
NHM-code op de CIM heet in het register "vak 24, 6 cijfers", maar "72" of
"7208 51" kwam er net zo goed doorheen en belandde zo op een officiële
spoorvrachtbrief. Een goederencode die niet bestaat is daar geen schoonheids-
foutje: de vervoerder rekent er zijn tarief mee en de douane leest hem.

De controle is generiek opgezet — een `pattern` in het documentregister — zodat
elk volgend veld met een vaste vorm hem meekrijgt zonder nieuwe code.
"""

import pytest

from app.services.documents.exporter import validate_document
from app.services.documents.registry import get_document
from tests.test_documents import BASE_VALUES, LINES


def cim_values(**overrides):
    """De CIM heeft meer verplichte velden; die zijn hier niet het onderwerp."""
    return dict(BASE_VALUES, **overrides)


def format_errors(values, language="nl"):
    errors, _ = validate_document(get_document("cim"), values, LINES, None, language)
    return [e for e in errors if "vorm" in e or "format" in e]


def test_a_six_digit_nhm_code_passes():
    assert format_errors(cim_values(nhm_code="720851")) == []


@pytest.mark.parametrize("code", ["72", "7208", "7208510", "7208 51", "72-08-51", "abcdef"])
def test_anything_that_is_not_six_digits_is_refused(code):
    errors = format_errors(cim_values(nhm_code=code))
    assert errors, f"{code!r} kwam er ongezien doorheen"


def test_the_message_says_what_the_field_should_look_like():
    """Een foutmelding die alleen zegt dát het fout is, laat de gebruiker
    raden."""
    errors = format_errors(cim_values(nhm_code="72"))
    assert "720851" in errors[0]


def test_the_message_is_translated():
    errors = format_errors(cim_values(nhm_code="72"), "en")
    assert errors and "six digits" in errors[0]


def test_an_empty_field_is_reported_as_missing_and_not_as_misformatted():
    """Twee verschillende problemen; ze allebei melden voor hetzelfde veld
    zou de gebruiker twee keer naar dezelfde regel sturen."""
    errors, _ = validate_document(get_document("cim"), cim_values(nhm_code=""),
                                  LINES, None, "nl")
    about_nhm = [e for e in errors if "NHM" in e]
    assert len(about_nhm) == 1
    assert "ontbreekt" in about_nhm[0]


def test_a_field_without_a_pattern_is_left_alone():
    """De controle mag alleen aanslaan waar het register een vorm belooft."""
    assert format_errors(cim_values(nhm_code="720851", consignor_name="Firma A")) == []
