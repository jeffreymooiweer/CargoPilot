"""The eleven rows ADR 2025 added, and the two it dropped.

The classification table this application is built on is an export of ADR
**2023**. That was not written down anywhere until the Dutch names were read out
of the book and the UN numbers on both sides were counted: the export has no
UN 0514 and no UN 3551 to 3560, and it still carries UN 1499 and UN 1999, which
ADR 2025 no longer knows.

Those eleven were not missing from the app — the IMDG 42-24 layer supplied them,
because the sea code adopted the same UN Model Regulations edition earlier. But
it supplied them with *sea* data. Transport category, tunnel restriction code and
hazard identification number exist only in ADR Table A, and so those three were
simply empty. Anyone shipping sodium-ion batteries by road got no points factor
at all, and the 1.1.3.6 table reported the line as incomplete without being able
to say what would complete it.

Eleven rows is few enough to take over by hand, and hand-copying is what the
repository does with a regulatory table anyway. What makes it defensible is the
same discipline as everywhere else: each row was read twice, from Table A and
from the alphabetical index of the same edition — two independent typesettings —
and the page it stands on is recorded with it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.dg.database import (
    get_un_entries,
    offline_lookup,
    search_un_numbers,
    withdrawn_un_numbers,
)

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg" / "adr_2025_additions.json"

ADDED = ["0514", "3551", "3552", "3553", "3554", "3555",
         "3556", "3557", "3558", "3559", "3560"]


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(SEED.read_text(encoding="utf-8"))


def test_the_seed_names_its_edition_and_its_cross_check(payload):
    assert payload["edition"] == "ADR 2025"
    assert "alfabetische index" in payload["cross_check"]
    assert [row["un"] for row in payload["entries"]] == ADDED


def test_every_row_says_which_page_it_came_from(payload):
    """A hand-copied regulatory row without a page reference cannot be checked
    by the next person, and this table is copied by hand on purpose."""
    assert all(row["page"] for row in payload["entries"])


#: What each row says, read off the printed page. Only the columns that ADR
#: holds and the sea code cannot supply are pinned here — the rest is already
#: cross-checked against the IMDG list elsewhere.
BY_HAND = {
    "0514": ("4", "E", ""),
    "3551": ("2", "E", ""),
    "3552": ("2", "E", ""),
    "3553": ("2", "B/D", "23"),
    "3554": ("3", "E", ""),
    "3555": ("2", "B", ""),
    # Vehicles get no transport category and no tunnel code in Table A, exactly
    # as UN 3166 and UN 3171 do not in the export — which is what makes the
    # empty value here a reading rather than a gap.
    "3556": ("", "", ""),
    "3557": ("", "", ""),
    "3558": ("", "", ""),
    "3559": ("4", "E", ""),
    "3560": ("1", "C/E", "668"),
}


@pytest.mark.parametrize("un", ADDED)
def test_the_road_columns_of_each_added_row(un):
    entry = get_un_entries(un)[0]
    category, tunnel, kemler = BY_HAND[un]
    assert entry["transport_category"] == category
    assert entry["tunnel_code"] == tunnel
    assert entry["hazard_number"] == kemler


def test_sodium_ion_batteries_can_be_counted_for_1_1_3_6():
    """The point of the whole exercise. Transport category 2 is a points factor
    of 3; without it the line was reported incomplete and the consignment had no
    exemption answer at all."""
    result = offline_lookup("3551", "nl", ["ADR"])
    assert result["transport_category"] == "2"
    assert result["tunnel_restriction_code"] == "(E)"
    assert "ADR 2025" in result["source"]


def test_disilane_carries_its_tunnel_code_and_kemler_number():
    result = offline_lookup("3553", "nl", ["ADR"])
    assert result["tunnel_restriction_code"] == "(B/D)"
    assert get_un_entries("3553")[0]["hazard_number"] == "23"


def test_these_entries_are_no_longer_marked_as_sea_only():
    """They were flagged `imdg_only` because the export did not have them, and
    that flag hides them from parts of the road side."""
    for un in ADDED:
        assert get_un_entries(un)[0].get("imdg_only") is not True, un


def test_the_source_note_names_the_book_and_the_page():
    note = get_un_entries("3560")[0]["source_note"]
    assert "ADR 2025" in note and "294" in note


def test_the_dutch_names_of_the_added_rows_are_there_too():
    assert get_un_entries("3551")[0]["name_nl"].startswith("NATRIUM-ION BATTERIJEN")
    assert "3551" in {hit["un"] for hit in search_un_numbers("natrium-ion", 10)}


# --- What ADR 2025 dropped -------------------------------------------------


def test_the_withdrawn_un_numbers_are_named():
    assert withdrawn_un_numbers() == {"1499", "1999"}


@pytest.mark.parametrize("un", ["1499", "1999"])
def test_a_withdrawn_entry_stays_findable_but_says_it_is_withdrawn(un):
    """Removing it would be worse: an older transport document may refer to it,
    and a lookup that returns nothing reads as "this UN number does not exist".
    What it must not do is pass for a current entry."""
    entry = get_un_entries(un)[0]
    assert entry["withdrawn_in"] == "ADR 2025"
    assert "Niet meer in ADR 2025" in entry["source_note"]


def test_an_ordinary_entry_is_not_marked_withdrawn():
    assert "withdrawn_in" not in get_un_entries("1203")[0]


def test_the_manifest_reports_the_addition_file():
    from app.services.regulatory_manifest import build_manifest

    files = [dataset["file"]
             for rule_set in build_manifest()["rule_sets"]
             for dataset in rule_set["datasets"]]
    assert "adr_2025_additions.json" in files


def test_the_manifest_says_the_table_is_a_2023_export():
    """The finding itself belongs in the manifest, not only in a changelog: an
    installation reporting edition "2025" while computing with a 2023 table is
    exactly the quiet mismatch the manifest exists to prevent."""
    from app.services.regulatory_manifest import build_manifest

    adr = next(r for r in build_manifest()["rule_sets"] if r["key"] == "adr")
    assert any("2023" in erratum for erratum in adr["errata"])
