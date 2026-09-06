"""The one number reader: what "1.250,5 L" says, and what "1.2.3" does not.

The rules are in ``services/quantities.py``; what is pinned here is that
each of them holds, that the sign survives, and that the three readers
which used to have a parser of their own — the compliance check, the LQ
measures and the IFTDGN — now read through this one.
"""
import pytest

from app.services.dg import compliance
from app.services.edifact import iftdgn
from app.services.quantities import parse_number, positive_number


@pytest.mark.parametrize("text,expected", [
    ("800 kg", 800.0),
    ("7", 7.0),
    ("12,5 L", 12.5),
    ("12.5", 12.5),
    ("0.500", 0.5),
    ("0,5", 0.5),
    # Both separators: the last one is the decimal.
    ("1.250,5 L", 1250.5),
    ("1,250.5", 1250.5),
    ("1.250.000,75", 1250000.75),
    # One separator, more than once: thousands.
    ("1.250.000", 1250000.0),
    ("1,250,000", 1250000.0),
    # One separator, once, exactly three digits after it: thousands.
    ("1.250", 1250.0),
    ("12,500 kg", 12500.0),
    ("999.000", 999000.0),
    # ... unless the head says otherwise.
    ("1000.000", 1000.0),
    ("0.250", 0.25),
    # A trailing separator is noise, not a fraction.
    ("5.", 5.0),
    # The sign is kept for the caller to refuse.
    ("-5 L", -5.0),
    ("-1.250,5", -1250.5),
])
def test_what_a_quantity_says(text, expected):
    assert parse_number(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "kg", "1.2.3,4", "1,23,456", "1.2345.6", "1,,2", None])
def test_what_is_not_a_number(text):
    assert parse_number(text) is None


def test_numbers_that_are_already_numbers():
    assert parse_number(3) == 3.0
    assert parse_number(2.5) == 2.5
    assert parse_number(float("nan")) is None
    assert parse_number(True) is None


def test_positive_means_greater_than_zero():
    assert positive_number("0") is None
    assert positive_number("-5 L") is None
    assert positive_number("5 L") == 5.0


def test_the_compliance_check_and_the_notification_read_through_the_same_parser():
    assert compliance._num("1.250,5 L") == 1250.5
    assert compliance._num("-5 L") == -5.0
    assert iftdgn._number("1.250,5 L") == 1250.5
    assert iftdgn._number("-5 L") is None
    # The LQ measures too: a thousands separator no longer splits the number.
    assert compliance._parse_measures("1.250,5 L") == [(1250500.0, "volume")]
