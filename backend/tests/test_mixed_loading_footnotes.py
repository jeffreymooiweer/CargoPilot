"""The empty cells of table 7.5.2.1 are not all empty.

Reported from practice: blasting explosive together with ammonium nitrate was
refused, while footnote (d) expressly permits it. The message the application
gave even named that exception — and then refused anyway. That is the most
annoying kind of fault: the screen proves the rule was known and that nothing was
done with it.

The cause was the shape of the check. It looked at whether there was a class 1
package somewhere in the consignment and a package of another class somewhere,
and then gave one error message about the whole consignment. Table 7.5.2.1 does
not work like that: it sets label against label, cell by cell, and three of those
cells hold a letter instead of nothing.

The text was checked in ADR 2025 Volume II (ECE/TRANS/352 Vol. II), table
7.5.2.1, printed page 592. Footnote (d) reads there:

    "Mixed loading permitted between blasting explosives (except UN No. 0083
     explosive, blasting, type C) and ammonium nitrate (UN Nos. 1942 and 2067),
     ammonium nitrate emulsion or suspension or gel (UN No. 3375) and alkali
     metal nitrates and alkaline earth metal nitrates provided the aggregate is
     treated as blasting explosives under Class 1 for the purposes of
     placarding, segregation, stowage and maximum permissible load."

That last condition is not a subordinate clause. Whoever relies on (d) moves the
placarding and the maximum permissible load of 7.5.5.2.1 to class 1. Permitting
without saying so would merely reverse the mistake.
"""

import pytest

from app.services.dg.compliance import check_adr_mixed_loading

# UN 0081 explosive, blasting, type A — a blasting explosive as footnote (d) means it.
BLASTING = {"un_number": "0081", "class": "1.1D",
            "proper_shipping_name": "EXPLOSIVE, BLASTING, TYPE A"}
# UN 0083 is excepted in so many words.
TYPE_C = {"un_number": "0083", "class": "1.1D",
          "proper_shipping_name": "EXPLOSIVE, BLASTING, TYPE C"}
AMMONIUM_NITRATE = {"un_number": "1942", "class": "5.1",
                    "proper_shipping_name": "AMMONIUM NITRATE"}
PAINT = {"un_number": "1263", "class": "3", "proper_shipping_name": "PAINT"}


def load(*products, language="en"):
    entries = [{"line_id": "L1", "products": list(products)}]
    return check_adr_mixed_loading(entries, language)


def by_rule(warnings, prefix):
    return [w for w in warnings if w["rule"].startswith(prefix)]


def errors(warnings):
    return [w for w in warnings if w["severity"] == "error"]


# --- The message itself ---------------------------------------------------


def test_blasting_explosives_with_ammonium_nitrate_are_no_longer_refused():
    assert errors(load(BLASTING, AMMONIUM_NITRATE)) == []


def test_the_footnote_that_permits_it_is_named():
    [warning] = by_rule(load(BLASTING, AMMONIUM_NITRATE), "ADR 7.5.2.1")
    assert warning["rule"] == "ADR 7.5.2.1 (d)"
    assert warning["severity"] == "warning"


def test_the_condition_travels_with_the_permission():
    """Permitting without the condition is a second fault, not a solution."""
    [warning] = by_rule(load(BLASTING, AMMONIUM_NITRATE), "ADR 7.5.2.1")
    message = warning["message"].lower()
    assert "placarding" in message
    assert "maximum permissible load" in message
    assert "7.5.5.2.1" in warning["message"]


def test_both_packages_are_named_in_the_outcome():
    [warning] = by_rule(load(BLASTING, AMMONIUM_NITRATE), "ADR 7.5.2.1")
    assert "0081" in warning["products"] and "1942" in warning["products"]


# --- The limits of footnote (d) -------------------------------------------


def test_type_c_is_excluded_by_the_footnote_itself():
    """"(except UN No. 0083 explosive, blasting, type C)" — that is the whole
    reason the number sits separately in the configuration."""
    assert errors(load(TYPE_C, AMMONIUM_NITRATE))


def test_an_explosive_that_is_not_a_blasting_explosive_stays_refused():
    """UN 0336 is fireworks. Footnote (d) is about blasting explosives."""
    fireworks = {"un_number": "0336", "class": "1.4G"}
    assert errors(load(fireworks, AMMONIUM_NITRATE))


def test_a_class_5_1_substance_outside_the_list_stays_refused():
    """Not every oxidising commodity is a nitrate the footnote names."""
    peroxide = {"un_number": "2014", "class": "5.1"}
    assert errors(load(BLASTING, peroxide))


@pytest.mark.parametrize("un,what", [
    ("2067", "ammonium nitrate based fertilizer"),
    ("3375", "ammonium nitrate emulsion"),
    ("1498", "sodium nitrate, an alkali metal nitrate"),
    ("1486", "potassium nitrate, an alkali metal nitrate"),
    ("1454", "calcium nitrate, an alkaline earth metal nitrate"),
    ("1507", "strontium nitrate, an alkaline earth metal nitrate"),
])
def test_every_nitrate_the_footnote_names_is_covered(un, what):
    """The footnote lists the nitrates with their numbers; skipping them would
    leave out half the provision."""
    assert errors(load(BLASTING, {"un_number": un, "class": "5.1"})) == [], what


# --- Per pair, not per consignment ----------------------------------------


def test_a_permitted_pair_does_not_excuse_a_forbidden_one():
    """The explosive may travel with the nitrate, but not with the paint. If the
    check judges the whole consignment, exactly that distinction disappears."""
    warnings = load(BLASTING, AMMONIUM_NITRATE, PAINT)
    [error] = errors(warnings)
    assert "1263" in error["products"]
    assert "1942" not in error["products"]


def test_and_the_permission_survives_alongside_the_refusal():
    warnings = load(BLASTING, AMMONIUM_NITRATE, PAINT)
    assert by_rule(warnings, "ADR 7.5.2.1 (d)")


def test_the_ordinary_prohibition_is_untouched():
    error = errors(load(BLASTING, PAINT))
    assert len(error) == 1
    assert error[0]["rule"] == "ADR 7.5.2.1"


# --- De andere twee voetnoten ---------------------------------------------


def test_life_saving_appliances_are_permitted_under_b():
    """UN 2990 is a life-saving appliance of class 9."""
    warnings = load(BLASTING, {"un_number": "2990", "class": "9"})
    assert errors(warnings) == []
    assert by_rule(warnings, "ADR 7.5.2.1 (b)")


def test_a_class_9_that_is_not_a_life_saving_appliance_stays_refused():
    assert errors(load(BLASTING, {"un_number": "3082", "class": "9"}))


def test_the_safety_device_pair_is_permitted_under_c():
    """UN 0503 with UN 3268 — pyrotechnically and electrically activated."""
    warnings = load({"un_number": "0503", "class": "1.4G"},
                    {"un_number": "3268", "class": "9"})
    assert errors(warnings) == []
    assert by_rule(warnings, "ADR 7.5.2.1 (c)")


def test_one_four_s_is_still_no_obstacle_at_all():
    """Footnote (a) permits 1.4S everywhere; that already worked and must stay so."""
    assert load({"un_number": "0012", "class": "1.4S"}, PAINT) == []


# --- What else must not change --------------------------------------------


def test_a_shipment_without_class_one_says_nothing_about_7_5_2_1():
    assert by_rule(load(PAINT, AMMONIUM_NITRATE), "ADR 7.5.2.1") == []


@pytest.mark.parametrize("language", ["nl", "en", "de"])
def test_the_footnote_speaks_every_interface_language(language):
    [warning] = by_rule(load(BLASTING, AMMONIUM_NITRATE, language=language), "ADR 7.5.2.1")
    assert "7.5.5.2.1" in warning["message"]
    assert len(warning["message"]) > 80


def test_the_condition_reaches_the_document_and_not_only_the_screen():
    """The condition of (d) moves the placarding and the maximum permissible
    load. That does not survive the session if it is only on the screen.
    """
    from app.services.documents.exporter import get_document, validate_document

    line = [{"line_id": "L1", "products": [
        dict(BLASTING, quantity_packages="1", type_of_package="box"),
        dict(AMMONIUM_NITRATE, quantity_packages="1", type_of_package="box"),
    ]}]
    errors_out, warnings_out = validate_document(get_document("cmr"), {}, [], line, "en")
    assert any("7.5.2.1 (d)" in warning for warning in warnings_out)
    assert not any("7.5.2.1:" in error for error in errors_out)


def test_the_source_of_the_numbers_is_recorded():
    """These numbers come from a text that is not in the repository. Where they
    come from should then be in it."""
    from app.services.dg.compliance import get_compliance_rules

    source = get_compliance_rules()["adr_mixed_loading"]["_footnotes_source"]
    assert "7.5.2.1" in source and "ECE/TRANS/352" in source


def test_the_rail_check_is_recorded_too():
    """Borrowing a prohibition from another regime is cautious; borrowing a
    permission is not. These footnotes apply to rail as well because RID has them
    word for word — checked, not assumed."""
    from app.services.dg.compliance import get_compliance_rules

    rail = get_compliance_rules()["adr_mixed_loading"]["_footnotes_rail"]
    assert "RID 2025" in rail and "7.5.2.1" in rail


def test_rail_gets_the_same_answer_as_road_under_its_own_name():
    """The same answer, cited to the regulation governing the document.

    The footnote is word for word the same in both texts, so the finding is the
    same finding. Its name is not: "ADR 7.5.2.1" printed on a CIM is the same
    kind of inaccuracy as the CV28 that used to appear there where the RID says
    CW 28 — a code name the regulation governing that document does not have.
    """
    from app.services.dg.compliance import check_compliance

    entries = [{"line_id": "L1", "products": [BLASTING, AMMONIUM_NITRATE]}]
    messages = set()
    for profile in ("ADR", "RID"):
        out = check_compliance(entries, [profile], "en")["adr_mixed_loading"]
        cited = [w for w in out if w["rule"].endswith("7.5.2.1 (d)")]
        assert [w["rule"] for w in cited] == [f"{profile} 7.5.2.1 (d)"], profile
        messages.add(cited[0]["message"])
    assert len(messages) == 1, messages
