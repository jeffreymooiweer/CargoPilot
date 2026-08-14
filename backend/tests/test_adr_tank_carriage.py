"""May these goods travel in a tank at all — and does the application know?

Everything in the compliance layer was written for **packages**, and said so
nowhere. A consignor filling in a tank load got the packages answer with nothing
to mark it as the wrong one. That is the most expensive shape of wrong this
application can produce, because it does not look like a gap; it looks like an
answer.

`carriage_mode` is the field that lets a check tell the difference, and this is
the first check that uses it. The admission rule sits in the explanation of
table A's own columns (ADR 3.2.1, Dutch edition, printed pages 546-547), and the
two tank columns do not say the same thing:

- **Column (12), ADR tanks** — where no code is given, carriage in ADR tanks is
  not permitted; the sentence carries no exception.
- **Column (10), portable tanks** — where no code is given, carriage in portable
  tanks is not permitted *unless the competent authority allows it* under
  6.7.1.3.

Rounding those two to one answer would either invent a prohibition or hide one.
What is pinned below is mostly that they stay apart, and that a packages
consignment is left exactly as it was.
"""

import pytest

from app.schemas.dg_compliance import DangerousGoodsProduct
from app.services.dg.compliance import check_adr_tank_admission, check_compliance


def line(*products):
    return [{"line_id": "L1", "products": list(products)}]


def product(un, mode=None, **extra):
    row = {"un_number": un, **extra}
    if mode:
        row["carriage_mode"] = mode
    return row


# --- the field itself ------------------------------------------------------


def test_absent_means_packages():
    """Every consignment drawn up before this release was packages, and none of
    them said so. The default has to be the one that keeps them right."""
    assert DangerousGoodsProduct(un_number="1203").carriage_mode is None


def test_an_unknown_mode_is_refused_at_the_edge():
    """A typo must not fall back to packages — that is the very failure this
    field exists to end."""
    with pytest.raises(ValueError):
        DangerousGoodsProduct(un_number="1203", carriage_mode="tanks")


@pytest.mark.parametrize("mode", ["packages", "tank", "portable_tank", "bulk"])
def test_the_four_modes_are_accepted(mode):
    assert DangerousGoodsProduct(un_number="1203", carriage_mode=mode).carriage_mode == mode


# --- column (12): no code, no carriage -------------------------------------


def test_petrol_may_travel_in_an_adr_tank():
    out = check_adr_tank_admission(line(product("1203", "tank")))
    assert out["status"] == "ok"
    item = out["items"][0]
    assert item["permitted"] is True
    assert item["tank_code"] == "LGBF"
    assert item["tank_vehicle"] == "FL"


def test_an_explosive_may_not():
    """UN 0004 leaves every tank column empty, and v1.65.0 deliberately refused
    to read that as a prohibition until the text had been read. It has been."""
    out = check_adr_tank_admission(line(product("0004", "tank")))
    assert out["status"] == "not_permitted"
    item = out["items"][0]
    assert item["permitted"] is False
    assert item["provision"] == "3.2.1 column (12)"
    assert "kolom (12)" in item["message"]


def test_the_refusal_names_the_substance():
    out = check_adr_tank_admission(
        line(product("1203", "tank"), product("0004", "tank")))
    refused = [i for i in out["items"] if not i["permitted"]]
    assert [i["position"] for i in refused] == ["UN 0004"]
    assert out["status"] == "not_permitted"


# --- column (10): the exception the other column does not have --------------


def test_a_portable_tank_without_an_instruction_is_not_flatly_refused():
    """Column (10) permits the competent authority to allow it under 6.7.1.3.
    Reporting that as a plain prohibition would invent one."""
    out = check_adr_tank_admission(line(product("0004", "portable_tank")))
    item = out["items"][0]
    assert item["permitted"] is False
    assert item["subject_to_approval"] is True
    assert "6.7.1.3" in item["message"]
    # and it does not block the consignment the way column (12) does
    assert out["status"] == "ok"


def test_a_portable_tank_with_an_instruction_reports_it():
    out = check_adr_tank_admission(line(product("1203", "portable_tank")))
    item = out["items"][0]
    assert item["permitted"] is True
    assert item["portable_tank_instructions"] == "T4"


# --- packages are left alone ------------------------------------------------


def test_a_packages_consignment_is_not_judged_here():
    assert check_adr_tank_admission(
        line(product("1203", "packages")))["status"] == "not_checked"


def test_a_consignment_without_a_mode_is_not_judged_here():
    assert check_adr_tank_admission(line(product("1203")))["status"] == "not_checked"


def test_bulk_is_not_a_tank():
    """Bulk has its own columns (16) and (17) and its own answer. Judging it
    against the tank columns would refuse loads the ADR permits."""
    assert check_adr_tank_admission(
        line(product("1203", "bulk")))["status"] == "not_checked"


# --- and it reaches the compliance result -----------------------------------


def test_the_outcome_is_in_the_compliance_result():
    out = check_compliance(line(product("0004", "tank", **{"class": "1"})), ["ADR"], "nl")
    assert out["adr_tank_admission"]["status"] == "not_permitted"


def test_a_packages_consignment_carries_no_tank_section():
    """A section that appeared on every consignment would be noise on the many
    that travel in packages."""
    out = check_compliance(line(product("1203", **{"class": "3"})), ["ADR"], "nl")
    assert "adr_tank_admission" not in out


# --- 8.6.4: the stricter side, which was in the table all along -------------
#
# Five codes carry two answers: B/D, B/E, C/D, C/E and D/E bar more tunnel
# categories for carriage in tanks and in bulk than for packages. Both lists
# have been in this repository's configuration since v1.50.0 and only the
# packages one was ever read, because nothing knew how the goods travelled. The
# note under the tunnel card said as much — and a note is not a check.


def tunnel(mode=None, code="(D/E)", **extra):
    from app.services.dg.compliance import check_adr_tunnel
    row = {"un_number": "1203", "class": "3", "tunnel_code": code,
           "transport_category": "2", "adr_total_quantity": "5000", **extra}
    if mode:
        row["carriage_mode"] = mode
    return check_adr_tunnel(line(row), "nl", points_status="above_threshold")


def test_packages_keep_the_answer_they_had():
    """The whole point of defaulting to packages: nothing already right moves."""
    assert tunnel()["restricted_categories"] == ["E"]
    assert tunnel("packages")["restricted_categories"] == ["E"]


def test_a_tank_is_barred_from_more_tunnels_than_packages():
    out = tunnel("tank")
    assert out["restricted_categories"] == ["D", "E"]
    assert out["carriage"] == "tanks_or_bulk"


def test_bulk_is_judged_with_the_tanks_column():
    """8.6.4 puts bulk on the same side as tanks — the one place in this release
    where bulk is not simply left alone."""
    assert tunnel("bulk")["restricted_categories"] == ["D", "E"]


def test_a_portable_tank_is_a_tank_here_too():
    assert tunnel("portable_tank")["restricted_categories"] == ["D", "E"]


def test_a_code_with_one_answer_is_unchanged_by_the_mode():
    """Only five of the twelve codes have two sides. Code E has one, and a mode
    that changed it would be inventing a restriction."""
    assert tunnel("packages", code="(E)")["restricted_categories"] == \
        tunnel("tank", code="(E)")["restricted_categories"]


def test_one_tank_position_decides_for_the_whole_load():
    """8.6.3.2 assigns one code to the whole load, so a single tank position
    cannot be answered as packages because the rest of the load is."""
    from app.services.dg.compliance import check_adr_tunnel
    out = check_adr_tunnel(line(
        {"un_number": "1203", "class": "3", "tunnel_code": "(D/E)",
         "transport_category": "2", "adr_total_quantity": "5000",
         "carriage_mode": "packages"},
        {"un_number": "1203", "class": "3", "tunnel_code": "(D/E)",
         "transport_category": "2", "adr_total_quantity": "5000",
         "carriage_mode": "tank"}), "nl", points_status="above_threshold")
    assert out["restricted_categories"] == ["D", "E"]


# --- 5.3.2.1.2 against 5.3.2.1.6: permitted is not required -----------------
#
# For packages 5.3.2.1.6 *permits* the two numbers on the front and rear plates,
# and only where a single substance is on board. For a tank vehicle 5.3.2.1.2
# *requires* them, on both sides of every tank and every compartment, for each
# substance that compartment carries. Those are not the same finding, and a tank
# load used to be shown the permitted one.


def placarding(mode=None, hazard="33", **extra):
    from app.services.dg.compliance import check_adr_placarding
    row = {"un_number": "1203", "class": "3", "hazard_number": hazard, **extra}
    if mode:
        row["carriage_mode"] = mode
    return check_adr_placarding(line(row), "nl")


def kinds(out):
    return {mark["kind"] for mark in out["marks"]}


def test_packages_get_the_permission_of_5_3_2_1_6():
    out = placarding()
    assert "numbered_plates" in kinds(out)
    assert "tank_plates" not in kinds(out)


def test_a_tank_gets_the_obligation_of_5_3_2_1_2():
    out = placarding("tank")
    assert "tank_plates" in kinds(out)
    assert "numbered_plates" not in kinds(out)
    mark = next(m for m in out["marks"] if m["kind"] == "tank_plates")
    assert mark["provision"] == "5.3.2.1.2"
    assert mark["required"] is True
    assert "33 / UN 1203" in mark["message"]


def test_the_front_and_rear_plates_are_required_either_way():
    """5.3.2.1.1 does not move: the plain orange plates stay on both."""
    for mode in (None, "tank"):
        assert "orange_plates" in kinds(placarding(mode))


def test_a_tank_without_a_hazard_number_is_told_the_rule_hangs_on_one():
    """5.3.2.1.2 opens on column (20) carrying a number. Where it does not, the
    check says so rather than printing a plate with a gap in it."""
    out = placarding("tank", hazard="")
    mark = next(m for m in out["marks"] if m["kind"] == "tank_plates")
    assert mark["required"] is None
    assert "1203" in mark["message"]


def test_a_portable_tank_is_a_tank_for_the_plates_too():
    assert "tank_plates" in kinds(placarding("portable_tank"))


def test_bulk_is_not_given_the_tank_plate_rule():
    """5.3.2.1.2 names tank vehicles and battery vehicles. Bulk has its own
    provisions, and answering it here would be the borrowing this release is
    supposed to end."""
    assert "tank_plates" not in kinds(placarding("bulk"))
