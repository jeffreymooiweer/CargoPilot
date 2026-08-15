"""The placarding sheet, and the two defects building it uncovered.

CargoPilot has derived chapter 5.3 since v1.53.0 and shown it on screen only.
The person who needs that answer is standing at the back of a trailer with
plates in his hand; a browser panel is not a thing you hold while doing that.
So the answer is now a sheet — and putting it on paper is what made two errors
in the answer itself visible.

Both were about a tank load being answered as if it were packages:

- **`placards_required` counted only the placards chosen by class.** 5.3.1.5
  picks placards by class, so those findings carry one; 5.3.1.4.1 picks them
  because the load is in a tank, and that finding carries `required` instead.
  A tank of petrol therefore reported that no placards were required while the
  finding right above it said the opposite.
- **5.3.6.1 hangs the environmentally hazardous mark on the placard**, so the
  same miscount made that mark wrong for a tank in the same breath.
- And the answer described itself as "computed for carriage in packages"
  whatever the mode of carriage was.
"""
import fitz
import pytest

from app.services.dg import database
from app.services.dg.compliance import check_adr_placarding
from app.services.documents.placarding_sheet import TEXT, render_placarding_sheet
from app.services.documents.registry import get_document


def product(un, **extra):
    """A product as the prepare step hands it on: table A already applied."""
    row = database.get_un_entries(un)[0]
    values = {
        "un_number": un,
        "proper_shipping_name": row.get("name_nl"),
        "class": row.get("class"),
        "classification_code": row.get("classification_code"),
        "labels": row.get("labels"),
        "hazard_number": row.get("hazard_number"),
    }
    values.update(extra)
    return values


def goods(*products):
    return [{"line_id": "L1", "products": list(products)}]


def text_of(path):
    with fitz.open(path) as pdf:
        return "\n".join(page.get_text() for page in pdf)


# --- what putting it on paper found ---------------------------------------


def test_a_tank_load_knows_it_needs_placards():
    """5.3.1.4.1 requires a placard of every label model of the load on both
    sides and the back. The finding said so; the summary flag said the
    opposite, because it counted only the placards 5.3.1.5 picks by class."""
    result = check_adr_placarding(goods(product("1203", carriage_mode="tank")), "nl")
    assert result["placards_required"] is True
    assert any(p["provision"] == "5.3.1.4.1" and p["required"] for p in result["placards"])


def test_packaged_petrol_still_needs_none():
    """The point of the check is that it says no: packaged flammable liquid
    puts no placard on the truck, and the orange plates are the whole of it."""
    result = check_adr_placarding(goods(product("1203")), "nl")
    assert result["placards_required"] is False


def test_the_answer_says_what_it_was_computed_for():
    assert check_adr_placarding(goods(product("1203")), "nl")["scope"] == "packages"
    assert check_adr_placarding(
        goods(product("1203", carriage_mode="tank")), "nl")["scope"] == "tanks_or_bulk"


# --- the sheet ------------------------------------------------------------


def test_the_sheet_carries_the_plates_a_tank_needs():
    """Everything the person at the back of the trailer has to know: the label
    model, the numbers for the orange plate, and the provision for each."""
    path = render_placarding_sheet(
        {"reference": "CP-1", "vehicle_registration": "12-BXG-3"}, [],
        goods(product("1203", carriage_mode="tank")), "nl")
    body = text_of(path)
    assert "5.3.1.4.1" in body
    assert "33 / UN 1203" in body
    assert "12-BXG-3" in body
    assert "UN" in body and "1203" in body


def test_the_sheet_says_when_nothing_is_required():
    """A sheet that lists nothing under "placards" would read as an oversight.
    It says the finding out loud instead."""
    path = render_placarding_sheet({}, [], goods(product("1203")), "nl")
    body = text_of(path)
    assert TEXT["scope_packages"]["nl"] in body


def test_the_sheet_never_claims_to_be_the_placard():
    """A diamond off a laser printer is not a placard, and a sheet that looks
    like one invites exactly that mistake."""
    path = render_placarding_sheet({}, [], goods(product("0004")), "nl")
    assert "5.3.1.7" in text_of(path)


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_the_sheet_speaks_all_four_languages(language):
    path = render_placarding_sheet(
        {}, [], goods(product("1203", carriage_mode="tank")), language)
    body = text_of(path)
    assert TEXT["title"][language] in body
    assert TEXT["placards"][language] in body


def test_the_document_is_registered_for_adr_with_dangerous_goods():
    """It reaches the wizard through the registry like every other document,
    and only where the profile is ADR and there are dangerous goods."""
    document = get_document("placarding_sheet")
    assert document is not None
    assert document["dg_profile"] == "ADR"
    assert document["dg_only"] is True
    assert document["exporter"] == "placarding"
    for language in ("nl", "en", "de", "fr"):
        assert document["label"][language]
        assert document["issue_status"][language]
