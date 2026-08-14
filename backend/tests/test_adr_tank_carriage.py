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
