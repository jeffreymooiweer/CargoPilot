"""One UN number, several Table A rows — and the app used to pick one in silence.

This is the most expensive thing found while going through the ADR side, and it
is worth writing down exactly why, because the old code looked reasonable.

It chose the row by **packing group**, and warned when a UN number had more than
one of those. That covers UN 1263 paint and UN 1993 n.o.s. flammable liquid and
it reads like the whole problem. It is not.

**UN 1950, aerosols, has twelve rows in Table A and none of them has a packing
group.** They are told apart by the classification code of column (3b):

| Code | Labels | Transport category | Tunnel code |
|---|---|---|---|
| 5A | 2.2 | 3 | E |
| 5F | 2.1 | 2 | D |
| 5T | 2.2 + 6.1 | 1 | D |

A user shipping ordinary flammable spray cans — the common case, by a distance —
was given the row for the non-flammable ones. Transport category 3 instead of 2
is a points factor of 1 where the ADR says 3, so a load of aerosols scored a
third of what it should and could keep an exemption it had lost. The tunnel code
came out E where it should be D, and the flammability label was missing from the
document. No warning, because every row has the same (empty) packing group.

UN 2037, gas cartridges, has nine rows with the same shape. UN 0015, 0016 and
0303 have three each that differ only in whether the ammunition carries a
corrosive or a toxic label — a subsidiary hazard silently dropped from the
description line. And even choosing a packing group does not always settle it:
UN 1263 has three PG III rows, one with tunnel code D/E and Kemler number 30 and
two with tunnel code E and neither.

Fifteen UN numbers were affected. The fix is to select on the classification code
first, and to say what is still open rather than to say nothing.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import pytest

from app.services.dg.autofill import (
    TABLE_A_VARIANT_FIELDS,
    derive_product,
    select_table_a_row,
    table_a_variant_note,
)
from app.services.dg.database import get_un_entries

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg" / "un_numbers.json"


def derived(un: str, **product) -> dict:
    return derive_product({"un_number": un, **product}, "nl", ["ADR"])


# --- The case that started it ---------------------------------------------


def test_aerosols_have_twelve_rows_and_no_packing_group_to_tell_them_apart():
    """The premise. If this ever stops holding, the rest of this file is about a
    problem that no longer exists and should be re-read rather than adjusted."""
    rows = get_un_entries("1950")
    assert len(rows) == 12
    assert {row["packing_group"].strip() for row in rows} == {""}
    assert len({row["classification_code"] for row in rows}) == 12


def test_flammable_aerosols_are_not_filled_in_as_non_flammable_ones():
    """5F is flammable: class 2.1, transport category 2, tunnel code D. Getting
    5A instead understates the points by a factor of three."""
    patch = derived("1950", classification_code="5F")["patch"]
    assert patch["class"] == "2.1"
    assert patch["transport_category"] == "2"
    assert patch["tunnel_code"] == "D"


def test_without_a_classification_code_the_first_row_is_filled_but_said_so():
    """Filling something in is still right — the user has to start somewhere —
    but it must not look like an answer."""
    outcome = derived("1950")
    assert outcome["patch"]["classification_code"] == "5A"
    note = outcome["hints"]["table_a_variant_note"]
    assert "12" in note
    assert "5F" in note and "5T" in note
    # It names what differs, so the user can judge whether it matters.
    assert "vervoerscategorie" in note and "tunnelcode" in note


def test_the_note_says_which_field_settles_it():
    """"Check the packing group" would be useless advice for UN 1950: every row
    has the same empty one. The classification code is what ADR distinguishes
    them by, and that is what the sentence asks for."""
    assert "classificatiecode" in derived("1950")["hints"]["table_a_variant_note"]


def test_gas_cartridges_have_the_same_shape():
    rows = get_un_entries("2037")
    assert len(rows) == 9
    assert derived("2037", classification_code="5F")["patch"]["class"] == "2.1"


# --- Rows no field the user fills in can tell apart ------------------------


def test_ammunition_rows_differing_only_in_the_label_are_not_pinned_on_a_code():
    """UN 0015 has three rows, all classification code 1.2G, differing only in
    whether a corrosive or a toxic label is carried. Telling the user to enter
    the classification code would be advice that cannot work, so the note says
    what the rows are and leaves the choice with them."""
    note = derived("0015")["hints"]["table_a_variant_note"]
    assert "1+8" in note and "1+6.1" in note
    assert "classificatiecode en verpakkingsgroep zijn voor alle rijen gelijk" in note


def test_choosing_the_packing_group_narrows_without_always_closing():
    """UN 1263 PG III is three rows: tunnel code D/E with Kemler 30, and twice
    tunnel code E with none. The old check went quiet as soon as a packing group
    was chosen and printed "(D/E)" on the document."""
    note = derived("1263", packing_group="III")["hints"]["table_a_variant_note"]
    assert "tunnelcode" in note
    assert "D/E" in note


def test_a_single_row_substance_says_nothing_at_all():
    """Most UN numbers have one row and must not gain a warning from this."""
    assert "table_a_variant_note" not in derived("1090")["hints"]


def test_rows_that_agree_on_everything_the_app_uses_say_nothing():
    """UN 1202 has nine rows in the Dutch table A and three in this export, and
    they differ only in a special provision the application does not compute
    with. A note there would be noise about a difference that changes nothing."""
    assert "table_a_variant_note" not in derived("1202")["hints"]


# --- Selecting the row ------------------------------------------------------


def test_the_classification_code_outranks_the_packing_group():
    """Both narrow, and the code is the finer of the two. Where they conflict —
    a code that does not occur with the entered group — neither is ignored:
    each filters what is left, and an impossible combination leaves the rows the
    other one allowed."""
    rows = get_un_entries("1263")
    entry, candidates = select_table_a_row(
        rows, {"classification_code": "F1", "packing_group": "II"})
    assert entry["packing_group"] == "II"
    assert all(row["packing_group"] == "II" for row in candidates)


def test_a_value_that_matches_nothing_does_not_empty_the_result():
    """A typo in the classification code must not leave the product without a
    row at all; the filter that yields nothing is simply not applied."""
    rows = get_un_entries("1950")
    entry, candidates = select_table_a_row(rows, {"classification_code": "9Z"})
    assert entry is rows[0]
    assert len(candidates) == 12


def test_matching_ignores_case_and_stray_spaces():
    rows = get_un_entries("1950")
    entry, _ = select_table_a_row(rows, {"classification_code": " 5f "})
    assert entry["classification_code"] == "5F"


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_the_note_is_written_in_the_language_of_the_screen(language):
    rows = get_un_entries("1950")
    note = table_a_variant_note(rows[0], rows, language)
    assert note and "1950" in note


# --- How many substances this concerns -------------------------------------


def test_every_silently_resolved_un_number_now_gets_a_note():
    """The measurement that turned this from a hunch into a defect: which UN
    numbers have several rows that the old packing-group check could not see.
    Fifteen, and every one of them now says so.

    Pinned as a list rather than a count, because the point is *which* ones —
    UN 1950 and UN 2037 are ordinary freight, not exotica.
    """
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    by_un: dict[str, list[dict]] = collections.defaultdict(list)
    for row in seed:
        by_un[row["un"]].append(row)

    invisible = []
    for un, rows in sorted(by_un.items()):
        if len(rows) < 2:
            continue
        if len({(row.get("packing_group") or "").strip().upper() for row in rows}) > 1:
            continue  # the old check saw these
        if any(len({(row.get(field) or "").strip() for row in rows}) > 1
               for field in TABLE_A_VARIANT_FIELDS):
            invisible.append(un)

    assert "1950" in invisible and "2037" in invisible and "0015" in invisible
    for un in invisible:
        assert "table_a_variant_note" in derived(un)["hints"], f"UN {un} stays silent"
