"""ADR 4.3.2.2: how full the tank may be, and what the application may claim.

Read in the English volume II and the printed Dutch edition, which agree word
for word on the arithmetic. 4.3.2.2.1 gives four maxima for a tank carrying a
substance liquid at normal temperatures, differing only in their numerator —
100, 98, 97, 95 — all over ``1 + α (50 − tF)``, with α from 4.3.2.2.2.

Which of the four applies turns on two things, and only one of them is in this
application's data. The tank's venting is the **fourth letter of the tank code**
the consignor types: N is a breather device or safety valves, H is hermetically
closed without a safety device. That half is read. The other half — toxic or
corrosive against merely flammable — is derived from the class and the
subsidiary risks, and is therefore *shown* as a derivation, so it can be
overruled rather than believed.

The part worth pinning hardest is what happens when the densities are missing,
which is the normal case: table A carries neither, so the answer is the formula
itself, and it goes on the document as a condition. A calculation whose inputs
nobody has must not come back as a number.
"""
import pytest

from app.services.dg.compliance import check_adr_filling_degree


def line(*products):
    return [{"line_id": "L1", "products": list(products)}]


def tank(un, code=None, **extra):
    product = {"un_number": un, "carriage_mode": "tank", **extra}
    if code:
        product["tank_code"] = code
    return product


def only(result):
    assert len(result["items"]) == 1, result["items"]
    return result["items"][0]


PETROL = {"density_15": "0.750", "density_50": "0.720", "filling_temperature": "15"}


# --- when it speaks at all -------------------------------------------------


def test_packages_are_not_asked_how_full_the_tank_is():
    assert check_adr_filling_degree(line({"un_number": "1203"}))["status"] == "not_checked"


def test_a_tank_always_gets_an_answer_even_without_the_densities():
    """The formula is the answer where the numbers are missing. Saying nothing
    would leave the consignor thinking 4.3.2.2 did not apply."""
    item = only(check_adr_filling_degree(line(tank("1203", "L4BN"))))
    assert item["status"] == "needs_input"
    assert item["provision"] == "4.3.2.2.1 (a)"
    assert "α" in item["formula"]
    assert "d15" in item["formula"]


# --- the four cases --------------------------------------------------------


def test_a_vented_tank_of_petrol_is_case_a():
    """Flammable, no toxic or corrosive subsidiary hazard, in a tank with a
    breather device: numerator 100. α = (0.750 − 0.720) / (35 × 0.720) and
    tF = 15 give 100 / 1.0417 = 96.0 %."""
    item = only(check_adr_filling_degree(line(tank("1203", "L4BN", **PETROL))))
    assert item["status"] == "computed"
    assert item["case"] == "a"
    assert item["numerator"] == 100
    assert item["degree"] == pytest.approx(96.0, abs=0.05)


def test_a_corrosive_in_the_same_tank_is_case_b():
    """Class 8 in a vented tank: numerator 98, not 100."""
    item = only(check_adr_filling_degree(line(tank(
        "1830", "L4BN", density_15="1.840", density_50="1.820",
        filling_temperature="20"))))
    assert item["case"] == "b"
    assert item["numerator"] == 98
    assert item["degree"] == pytest.approx(97.1, abs=0.05)


def test_hermetically_closed_drops_the_numerator():
    """The same petrol in an L4BH — hermetically closed, no safety device — is
    case (c): 97 rather than 100. The fourth letter of the tank code is the
    whole of that difference."""
    item = only(check_adr_filling_degree(line(tank("1203", "L4BH", **PETROL))))
    assert item["case"] == "c"
    assert item["numerator"] == 97
    assert item["degree"] == pytest.approx(93.1, abs=0.05)


def test_the_derivation_is_shown_and_not_hidden():
    """Which case applies is half read and half derived, and the derived half
    is stated so a consignor who knows better can overrule it."""
    item = only(check_adr_filling_degree(line(tank("1203", "L4BN", **PETROL))))
    assert "L4BN" in item["derivation"]
    assert item["provision"] in item["derivation"]


# --- where the provision hands over ----------------------------------------


def test_above_fifty_degrees_the_other_provision_applies():
    """4.3.2.2.3 takes over above 50 °C, with a flat 95 % ceiling and its own
    formula on two different densities. The application says so rather than
    computing with a formula that no longer applies."""
    item = only(check_adr_filling_degree(line(tank(
        "1203", "L4BN", filling_temperature="60"))))
    assert item["status"] == "above_fifty"
    assert item["provision"] == "4.3.2.2.3"
    assert "95" in item["message"]


def test_classes_one_five_two_and_seven_are_excepted():
    """The provision's own footnote sends them to 4.3.4.1.3."""
    item = only(check_adr_filling_degree(line(tank("0004", "L4BN"))))
    assert item["status"] == "own_rule"
    assert item["provision"] == "4.3.4.1.3"


def test_without_a_tank_code_the_case_cannot_be_chosen():
    """Venting decides between (a)/(b) and (c)/(d), and the tank code is where
    that is written. Without it the formula still stands, but not a case."""
    item = only(check_adr_filling_degree(line(tank("1203"))))
    assert item["status"] == "no_tank_code"
    assert "4.3.2.2.1" in item["provision"]


# --- the arithmetic itself -------------------------------------------------


def test_alpha_may_be_given_instead_of_the_two_densities():
    """A consignor who has the coefficient already should not have to work
    backwards to two densities that produce it."""
    item = only(check_adr_filling_degree(line(tank(
        "1203", "L4BN", expansion_coefficient="0.0011905",
        filling_temperature="15"))))
    assert item["status"] == "computed"
    assert item["degree"] == pytest.approx(96.0, abs=0.05)


def test_densities_that_cannot_give_a_coefficient_are_refused():
    """A liquid does not get denser as it warms. Where d15 is not above d50 the
    input is wrong, and a wrong α would give a filling degree that looks
    perfectly reasonable."""
    item = only(check_adr_filling_degree(line(tank(
        "1203", "L4BN", density_15="0.720", density_50="0.750",
        filling_temperature="15"))))
    assert item["status"] == "needs_input"


def test_filling_at_fifty_degrees_needs_no_correction():
    """At tF = 50 the correction term is zero and the degree is the numerator
    itself — the one point where the formula can be checked by looking at it."""
    item = only(check_adr_filling_degree(line(tank(
        "1203", "L4BN", density_15="0.750", density_50="0.720",
        filling_temperature="50"))))
    assert item["degree"] == pytest.approx(100.0, abs=0.05)


# --- and it has to reach the paper -----------------------------------------


def test_the_condition_reaches_the_document():
    """A condition that reaches the panel and not the paper is a condition the
    person filling in the document never meets — the exact failure the tank
    admission check had before v1.66.0, and the tank fit check had until now."""
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document

    values = {
        "consignor_name": "Afzender", "consignor_address": "Havenweg 1",
        "consignee_name": "Ontvanger", "consignee_address": "Hafenstrasse 4",
        "loading_point": "Rotterdam", "discharge_point": "Duisburg",
        "freight_payment": "Franco", "established_place": "Rotterdam",
        "established_date": "2026-08-15",
    }
    goods = [{"line_id": "1", "products": [{
        "un_number": "1203", "proper_shipping_name": "BENZINE", "class": "3",
        "packing_group": "II", "carriage_mode": "tank", "tank_code": "L4BN"}]}]
    _errors, warnings = validate_document(
        get_document("cmr"), values, [], goods, "nl")
    assert any("4.3.2.2" in warning for warning in warnings)


def test_a_tank_that_does_not_fit_reaches_the_document_too():
    """The 4.3 fit check shipped in v1.82.0 answering on screen only."""
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document

    values = {
        "consignor_name": "Afzender", "consignor_address": "Havenweg 1",
        "consignee_name": "Ontvanger", "consignee_address": "Hafenstrasse 4",
        "loading_point": "Rotterdam", "discharge_point": "Duisburg",
        "freight_payment": "Franco", "established_place": "Rotterdam",
        "established_date": "2026-08-15",
    }
    goods = [{"line_id": "1", "products": [{
        "un_number": "1203", "proper_shipping_name": "BENZINE", "class": "3",
        "packing_group": "II", "carriage_mode": "tank", "tank_code": "SGAN"}]}]
    _errors, warnings = validate_document(
        get_document("cmr"), values, [], goods, "nl")
    assert any("4.3" in warning and "SGAN" in warning for warning in warnings)
