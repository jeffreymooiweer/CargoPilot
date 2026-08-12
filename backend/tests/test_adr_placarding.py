"""ADR 5.3 — what goes on the outside of the vehicle, and mostly what does not.

Chapter 5.3 was the last of the seven gaps in `docs/dg-coverage.md`, carrying
the note that placarding is "the most common real-world failure". The
application named the chapter in its 1.1.3.6 output — "orange plates and
placards on the transport unit (chapter 5.3)" — and derived nothing.

That sentence was also wrong, in the direction that matters. **5.3.1.5 gives a
vehicle carrying packages exactly two reasons to placard**: 5.3.1.5.1 for class
1 other than division 1.4 compatibility group S, and 5.3.1.5.2 for class 7 in
packagings or IBCs other than excepted packages. A load of packaged petrol,
nitric acid or a toxic liquid needs no placard at all — the orange plates are
the whole of it.

Telling a driver to placard anyway is not a harmless excess. It teaches that the
placard is decoration, and the next load where it is class 1 on board is the one
where that lesson has already been learnt. So the tests below are as much about
the "no" as the "yes", and the "no" is a stated finding rather than an empty
list, because an empty list reads as "not computed".
"""
from __future__ import annotations

import pytest

from app.services.dg.compliance import check_adr_placarding


def load(*products, **entry):
    return [{**entry, "products": list(products)}]


PETROL = {"un_number": "1203", "class": "3", "labels": "3", "hazard_number": "33"}
AMMUNITION = {"un_number": "0015", "class": "1", "classification_code": "1.2G",
              "labels": "1"}
SAFETY_CARTRIDGE = {"un_number": "0012", "class": "1",
                    "classification_code": "1.4S", "labels": "1.4"}
RADIOACTIVE = {"un_number": "2915", "class": "7", "labels": "7"}
GREEN = {"un_number": "3082", "class": "9", "labels": "9", "hazard_number": "90",
         "environmentally_hazardous": True}


def kinds(result):
    return [mark["kind"] for mark in result["marks"]]


# --- the no ------------------------------------------------------------------

def test_packaged_petrol_needs_no_placard():
    """The case the old sentence got wrong, and the commonest load there is."""
    result = check_adr_placarding(load(PETROL), "en")
    assert result["placards_required"] is False


def test_the_absence_is_a_finding_and_not_an_empty_list():
    """"No placards" has to be said, with the provision that makes it so.

    An empty list is indistinguishable from a check that did not run, and a user
    who cannot tell those apart will assume the worse of the two and placard.
    """
    result = check_adr_placarding(load(PETROL), "en")
    assert len(result["placards"]) == 1
    note = result["placards"][0]
    assert note["class"] is None
    assert note["provision"] == "5.3.1.5"
    assert "5.3.1.5" in note["message"]
    assert "class 1 and class 7" in note["message"]


def test_division_1_4_compatibility_group_s_is_the_one_class_1_exception():
    """5.3.1.5.1 excepts it by name, and it is not a rare entry: UN 0012, 0014
    and 0055 are ordinary small-arms cartridges and safety devices."""
    assert check_adr_placarding(load(SAFETY_CARTRIDGE), "en")["placards_required"] is False


# --- the yes -----------------------------------------------------------------

def test_class_1_packages_placard():
    result = check_adr_placarding(load(AMMUNITION), "en")
    assert result["placards_required"] is True
    assert result["placards"][0]["class"] == "1"
    assert result["placards"][0]["provision"] == "5.3.1.5.1"


def test_class_7_packages_placard():
    result = check_adr_placarding(load(RADIOACTIVE), "en")
    assert result["placards_required"] is True
    assert result["placards"][0]["provision"] == "5.3.1.5.2"


def test_one_class_1_line_placards_the_whole_vehicle():
    """The placard is a property of the vehicle, not of the pallet."""
    result = check_adr_placarding(load(PETROL, AMMUNITION), "en")
    assert result["placards_required"] is True


# --- the orange plates -------------------------------------------------------

def test_every_dangerous_load_carries_two_orange_plates():
    result = check_adr_placarding(load(PETROL), "en")
    assert "orange_plates" in kinds(result)


def test_a_single_substance_gets_its_two_numbers_printed():
    """5.3.2.1.6 lets the front and rear plates carry the numbers instead of
    being blank, and both come out of table A — column (20) and column (1) — so
    the check can print them rather than describe them."""
    result = check_adr_placarding(load(PETROL), "en")
    numbered = [m for m in result["marks"] if m["kind"] == "numbered_plates"]
    assert len(numbered) == 1
    assert numbered[0]["hazard_number"] == "33"
    assert numbered[0]["un_number"] == "1203"
    assert "33 / UN 1203" in numbered[0]["message"]


def test_two_substances_get_no_numbers_because_5_3_2_1_6_does_not_apply():
    """It says "carrying only one dangerous substance and no non-dangerous
    substance". Two substances, and the plates stay blank."""
    result = check_adr_placarding(load(PETROL, GREEN), "en")
    assert "numbered_plates" not in kinds(result)


def test_within_the_exemption_there_are_no_plates_and_no_placards():
    """1.1.3.6.2 relieves the unit of both together."""
    result = check_adr_placarding(load(PETROL), "en", points_status="exempt")
    assert result["status"] == "exempt"
    assert kinds(result) == ["exempt"]
    assert result["placards_required"] is False


# --- the environmentally hazardous mark --------------------------------------

def test_the_vehicle_mark_hangs_on_the_placard_and_not_on_the_substance():
    """5.3.6.1 opens "When a placard is required to be displayed in accordance
    with the provisions of section 5.3.1".

    So packaged environmentally hazardous class 9 puts no mark on the truck —
    because 5.3.1.5 asks for no placard — while the same substance beside a
    class 1 line does. Reading 5.3.6 without its opening clause would mark every
    vehicle carrying a marine pollutant.
    """
    alone = check_adr_placarding(load(GREEN), "en")
    mark = [m for m in alone["marks"] if m["kind"] == "environmental_mark"]
    assert mark and mark[0]["applies"] is False

    beside_explosives = check_adr_placarding(load(GREEN, AMMUNITION), "en")
    mark = [m for m in beside_explosives["marks"] if m["kind"] == "environmental_mark"]
    assert mark and mark[0]["applies"] is True


def test_the_mark_on_the_package_is_not_relieved_by_this():
    """The sentence has to say so, or "not the case" reads as "no mark at all"
    and 5.2.1.8.3 is quietly dropped from the packages."""
    result = check_adr_placarding(load(GREEN), "en")
    mark = [m for m in result["marks"] if m["kind"] == "environmental_mark"][0]
    assert "5.2.1.8.3" in mark["message"]


# --- what it does not answer -------------------------------------------------

def test_the_answer_says_it_is_about_packages():
    """Tanks and bulk have their own subsections and a different answer —
    numbered plates on the sides under 5.3.2.1.2 and 5.3.2.1.4, and placards for
    every class rather than two. Saying which question was answered is the
    difference between a result and a guess."""
    assert check_adr_placarding(load(PETROL), "en")["scope"] == "packages"


def test_a_forbidden_substance_is_not_placarded():
    """It may not be offered for carriage at all; deriving its placard would be
    answering the wrong question politely."""
    forbidden = {"un_number": "1798", "class": "8", "labels": "8",
                 "transport_forbidden": True}
    assert check_adr_placarding(load(forbidden), "en")["status"] == "not_checked"


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_every_finding_speaks_the_four_languages(language):
    result = check_adr_placarding(load(GREEN, AMMUNITION), language)
    for item in result["placards"] + result["marks"]:
        assert item["message"].strip()
        assert "{" not in item["message"], item["message"]
