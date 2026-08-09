"""A field that promises a shape has to have that shape.

Until now the export only checked whether a mandatory field was filled. The NHM
code on the CIM is called "box 24, 6 digits" in the registry, but "72" or
"7208 51" got through just as easily and ended up on an official rail waybill
that way. A goods code that does not exist is no blemish there: the carrier
calculates its tariff with it and customs read it.

The check is set up generically — a `pattern` in the document registry — so that
every next field with a fixed shape gets it without new code.
"""

import pytest

from app.services.documents.exporter import validate_document
from app.services.documents.registry import get_document
from tests.test_documents import BASE_VALUES, LINES


def cim_values(**overrides):
    """The CIM has more mandatory fields; those are not the subject here."""
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
    """An error message that only says *that* it is wrong leaves the user
    guessing."""
    errors = format_errors(cim_values(nhm_code="72"))
    assert "720851" in errors[0]


def test_the_message_is_translated():
    errors = format_errors(cim_values(nhm_code="72"), "en")
    assert errors and "six digits" in errors[0]


def test_an_empty_field_is_reported_as_missing_and_not_as_misformatted():
    """Two different problems; reporting both for the same field would send the
    user to the same line twice."""
    errors, _ = validate_document(get_document("cim"), cim_values(nhm_code=""),
                                  LINES, None, "nl")
    about_nhm = [e for e in errors if "NHM" in e]
    assert len(about_nhm) == 1
    assert "ontbreekt" in about_nhm[0]


def test_a_field_without_a_pattern_is_left_alone():
    """The check may only fire where the registry promises a shape."""
    assert format_errors(cim_values(nhm_code="720851", consignor_name="Firma A")) == []
