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


# --- 1.10.3.1.2: the tank column, and the seven rows that only live there ---
#
# The table has three quantity columns — tank, bulk and packages — and only the
# packages one was answered. For packages the answer is mostly footnote b):
# whatever the quantity, 1.10.3 does not apply. Seven rows are b) in packages
# and **3,000 litres in a tank**, so they had no reason to exist here until the
# application knew about tanks. A road tanker of petrol is the plainest of them,
# and this check used to call it not high consequence.
#
# Footnotes c) and d) matter as much as the figures: a tank or bulk value counts
# only where table A admits that form of carriage.


def security(mode=None, quantity="5000", un="1203", hazard="3",
             group="II", code="F1"):
    from app.services.dg.compliance import check_adr_security
    row = {"un_number": un, "class": hazard, "packing_group": group,
           "classification_code": code}
    if quantity is not None:
        row["adr_total_quantity"] = quantity
    if mode:
        row["carriage_mode"] = mode
    return check_adr_security(line(row), "nl")


def qualifying(out):
    return [i for i in out["items"] if not i.get("not_answered")]


def test_a_tanker_of_petrol_above_three_thousand_litres_is_high_consequence():
    """The finding this release exists for. In packages the same petrol is
    footnote b) at any quantity; in a tank it crosses at 3,000 litres."""
    out = security("tank", "5000")
    assert out["status"] == "high_consequence"
    item = qualifying(out)[0]
    assert item["threshold_kg"] == 3000
    assert "3000" in item["threshold_note"]


def test_the_same_tanker_below_the_figure_is_not():
    assert security("tank", "2000")["status"] == "ok"


def test_packaged_petrol_stays_outside_1_10_3_at_any_quantity():
    """Footnote b), and the reason v1.58.0 could answer packages with a
    membership test and no arithmetic at all. That must not have changed."""
    assert security(None, "10000")["status"] == "ok"
    assert security("packages", "10000")["status"] == "ok"


def test_a_toxic_gas_in_a_tank_qualifies_at_any_quantity():
    """Its tank figure is 0, not 3,000 — the table does not treat every tank
    row the same and neither may the check."""
    out = security("tank", "1", un="1017", hazard="2", group="", code="2TC")
    assert out["status"] == "high_consequence"
    assert qualifying(out)[0]["threshold_kg"] == 0


def test_packing_group_ii_corrosive_stays_out_where_group_i_falls_in():
    """The row names packing group I. Reading it as "corrosives" would put a
    tanker of dilute acid under a security plan it does not need."""
    assert security("tank", "5000", un="1830", hazard="8", group="II",
                    code="C1")["status"] == "ok"
    assert security("tank", "5000", un="1830", hazard="8", group="I",
                    code="C1")["status"] == "high_consequence"


def test_a_missing_quantity_is_reported_rather_than_read_as_under():
    """A threshold needs a quantity. Absent, the honest answer is that the row
    was not answered — not that the load is below the figure."""
    out = security("tank", None)
    assert out["status"] == "ok"
    unanswered = [i for i in out["items"] if i.get("not_answered")]
    assert unanswered and unanswered[0]["threshold_kg"] == 3000


def test_footnote_c_keeps_a_substance_out_where_tanks_are_not_admitted():
    """An explosive has no tank code, so the tank column says nothing about it —
    and the admission check has already refused the consignment anyway."""
    assert security("tank", "5000", un="0004", hazard="1", group="",
                    code="1.1D")["status"] == "ok"


def test_an_explosive_in_packages_is_unchanged():
    assert security(None, "1", un="0004", hazard="1", group="",
                    code="1.1D")["status"] == "high_consequence"


# --- 1.1.3.6.2: the exemption is for packages ------------------------------
#
# The operative sentence grants it for goods carried **in packages** in one
# transport unit. A tank load is not carriage in packages, so the exemption is
# not available to it however small the quantity — and the points arithmetic,
# which exists only to test that exemption, is answering a question that does
# not arise. Withholding an exemption is the safe direction to be wrong in;
# granting one is not.


def points(mode=None, quantity="100"):
    from app.services.dg.compliance import check_adr_points
    row = {"un_number": "1203", "class": "3", "transport_category": "2",
           "adr_total_quantity": quantity}
    if mode:
        row["carriage_mode"] = mode
    return check_adr_points(line(row), ["ADR"], "nl")


def test_packages_can_still_claim_the_exemption():
    assert points()["status"] == "exempt_possible"
    assert points("packages")["status"] == "exempt_possible"


@pytest.mark.parametrize("mode", ["tank", "portable_tank", "bulk"])
def test_a_load_that_is_not_in_packages_cannot(mode):
    out = points(mode)
    assert out["status"] == "not_available_for_mode"
    assert "1.1.3.6.2" in out["mode_note"]
    assert out["not_in_packages"] == ["UN 1203"]


def test_a_tiny_tank_quantity_does_not_buy_the_exemption_back():
    """The exemption turns on the form of carriage, not on the amount. One
    litre in a tank is still not carriage in packages."""
    assert points("tank", "1")["status"] == "not_available_for_mode"


def test_the_tunnel_no_longer_treats_a_tank_load_as_exempt():
    """8.6.3.3 takes goods carried under 1.1.3 out of the tunnel determination.
    A tank load is not carried under 1.1.3, so its code stands — and before this
    it could be dropped as exempt on the strength of a points total."""
    from app.services.dg.compliance import check_adr_tunnel
    out = check_adr_tunnel(
        line({"un_number": "1203", "class": "3", "tunnel_code": "(D/E)",
              "transport_category": "2", "adr_total_quantity": "100",
              "carriage_mode": "tank"}),
        "nl", points_status="not_available_for_mode")
    assert out["status"] == "derived"
    assert out["restricted_categories"] == ["D", "E"]


# --- 5.3.1.4.1 against 5.3.1.5: the answer inverts --------------------------
#
# For packages a placard goes on the vehicle only for class 1 and class 7, which
# is why the packages answer is mostly that none is needed — the finding v1.57.0
# was built around. A tank does not work that way: every label model of the load
# goes on both long sides and the rear. Answering a tank with the packages rule
# turns a requirement into an absence, which is the worst direction for a
# placard to be wrong in.


def placards(mode=None, labels="3", un="1203", hazard="3"):
    from app.services.dg.compliance import check_adr_placarding
    row = {"un_number": un, "class": hazard, "labels": labels,
           "hazard_number": "33"}
    if mode:
        row["carriage_mode"] = mode
    return check_adr_placarding(line(row), "nl")["placards"]


def provisions(rows):
    return {row["provision"] for row in rows}


def test_packaged_petrol_still_needs_no_placard():
    """The finding v1.57.0 was built around, and it must survive."""
    assert provisions(placards()) == {"5.3.1.5"}


def test_a_tank_of_the_same_petrol_needs_one():
    rows = placards("tank")
    assert "5.3.1.4.1" in provisions(rows)
    assert "5.3.1.5" not in provisions(rows)
    vehicle = next(r for r in rows if r["provision"] == "5.3.1.4.1")
    assert vehicle["label_models"] == ["3"]
    assert vehicle["required"] is True


def test_the_tank_container_placement_is_named_beside_the_vehicle_one():
    """5.3.1.2 puts them on both long sides and each end of the tank container
    itself, which is a different placement from the vehicle's."""
    assert "5.3.1.2" in provisions(placards("tank"))


def test_bulk_is_placarded_like_a_tank():
    """5.3.1.4 is headed carriage in bulk and tanks alike — the one rule in this
    work where bulk and tanks share an answer."""
    assert "5.3.1.4.1" in provisions(placards("bulk"))


def test_every_label_model_of_the_load_is_named():
    from app.services.dg.compliance import check_adr_placarding
    rows = check_adr_placarding(line(
        {"un_number": "1203", "class": "3", "labels": "3",
         "carriage_mode": "tank"},
        {"un_number": "1017", "class": "2", "labels": "2.3+8",
         "carriage_mode": "tank"}), "nl")["placards"]
    vehicle = next(r for r in rows if r["provision"] == "5.3.1.4.1")
    assert vehicle["label_models"] == ["2.3", "3", "8"]


def test_a_tank_without_a_label_is_told_the_rule_hangs_on_one():
    rows = placards("tank", labels="")
    unresolved = [r for r in rows if r.get("required") is None]
    assert unresolved and "1203" in unresolved[0]["message"]
