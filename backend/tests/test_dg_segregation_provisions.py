"""Tests for the IMDG column 16b segregation provisions.

The class segregation table of 7.2.4 works on class. Column 16b adds provisions
per *substance* — "stow separated from acids" — which the app now knows for 840
UN numbers. The meaning of each SG code is read from the cards themselves rather
than typed from memory, because a wrong segregation rule is a safety-relevant
error, not a cosmetic one.

These tests pin the parsed rules and the behaviour that follows from them.
"""

import pytest

from app.services.dg.compliance import check_imdg_segregation_provisions
from app.services.dg.enrichment import card_data_for, segregation_provisions


def shipment(*products):
    return [{"line_id": 1, "products": list(products)}]


def codes(warnings):
    return sorted(w["rule"] for w in warnings)


@pytest.fixture(scope="module")
def rules():
    return segregation_provisions()


def test_the_provisions_were_parsed_from_the_cards(rules):
    assert len(rules) == 70
    actionable = [c for c, r in rules.items() if not r.get("informational")]
    assert len(actionable) == 48


def test_a_provision_naming_a_class_is_actionable(rules):
    assert rules["SG17"]["action"] == "separated_from"
    assert rules["SG17"]["targets"] == {"classes": ["5.1"]}


def test_a_provision_naming_a_segregation_group_is_actionable(rules):
    assert rules["SG35"]["action"] == "separated_from"
    assert rules["SG35"]["targets"] == {"groups": ["SGG1"]}


def test_a_provision_about_foodstuffs_stays_informational(rules):
    """"as in 7.3.4.2.2" is a cross-reference, not something to check against."""
    assert rules["SG29"]["informational"] is True


def test_an_exception_is_read_as_an_exception_not_a_second_target(rules):
    """"class 1 except for division 1.4S" — 1.4S is excluded, not targeted."""
    assert rules["SG14"]["targets"] == {"classes": ["1"]}
    assert rules["SG14"]["excepted_classes"] == ["1.4S"]


def test_ammonia_next_to_an_acid_is_reported():
    """UN 1005 carries SG35: stow separated from acids. UN 1789 is one."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "1005", "class": "2.3"}, {"un_number": "1789", "class": "8"}), "nl"
    )
    assert "IMDG 16b (SG35)" in codes(warnings)
    message = next(w for w in warnings if w["rule"] == "IMDG 16b (SG35)")["message"]
    # The group is named, not just coded, and the card's own wording follows.
    assert "SGG1 (Zuren)" in message
    assert "separated from" in message


def test_the_provision_is_applied_in_both_directions():
    """The acid also has to be kept away from the alkali, and says so itself."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "1005", "class": "2.3"}, {"un_number": "1789", "class": "8"}), "nl"
    )
    assert codes(warnings) == ["IMDG 16b (SG35)", "IMDG 16b (SG36)"]
    pairs = {w["rule"]: w["products"] for w in warnings}
    assert pairs["IMDG 16b (SG35)"].startswith("UN 1005")
    assert pairs["IMDG 16b (SG36)"].startswith("UN 1789")


def test_a_class_target_is_matched_on_the_declared_class():
    """UN 1017 chlorine carries SG19: separated from class 7."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "1017", "class": "2.3"}, {"un_number": "2912", "class": "7"}), "nl"
    )
    assert "IMDG 16b (SG19)" in codes(warnings)


def test_an_excepted_class_is_not_reported():
    """SG14 excludes division 1.4S; warning about it would be plain wrong."""
    with_11d = check_imdg_segregation_provisions(
        shipment({"un_number": "2211", "class": "9"}, {"un_number": "0004", "class": "1.1D"}), "nl"
    )
    with_14s = check_imdg_segregation_provisions(
        shipment({"un_number": "2211", "class": "9"}, {"un_number": "0012", "class": "1.4S"}), "nl"
    )
    assert "IMDG 16b (SG14)" in codes(with_11d)
    assert "IMDG 16b (SG14)" not in codes(with_14s)


def test_a_bare_class_target_covers_its_divisions():
    """"separated from class 1" applies to 1.1D as much as to 1.3G."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "2211", "class": "9"}, {"un_number": "0331", "class": "1.1D"}), "nl"
    )
    assert "IMDG 16b (SG14)" in codes(warnings)


def test_subsidiary_risks_count_towards_a_class_target():
    warnings = check_imdg_segregation_provisions(
        shipment(
            {"un_number": "1017", "class": "2.3"},
            {"un_number": "9999", "class": "8", "subsidiary_risks": "7"},
        ),
        "nl",
    )
    assert "IMDG 16b (SG19)" in codes(warnings)


def test_a_single_substance_raises_nothing():
    assert check_imdg_segregation_provisions(shipment({"un_number": "1005", "class": "2.3"}), "nl") == []


def test_two_acids_together_are_not_reported():
    """Neither nitric nor hydrochloric acid must be kept from acids."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "2031", "class": "8"}, {"un_number": "1789", "class": "8"}), "nl"
    )
    assert "IMDG 16b (SG35)" not in codes(warnings)
    assert card_data_for("2031")["segregation_codes"] == [
        "SG6", "SG16", "SG17", "SG19", "SG36", "SG49"
    ]


def test_english_reports_the_same_finding():
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "1005", "class": "2.3"}, {"un_number": "1789", "class": "8"}), "en"
    )
    message = next(w for w in warnings if w["rule"] == "IMDG 16b (SG35)")["message"]
    assert message.startswith("Stow separated from SGG1 (Acids)")
