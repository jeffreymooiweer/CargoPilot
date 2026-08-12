"""The table this application computes with is ADR 2025, read from the book.

Until v1.56.0 it was an export of ADR **2023**. That was written down honestly —
the manifest said so from v1.49.0 — and it was patched where the gap was
visible: the eleven rows 2025 added were transcribed by hand in v1.52.0 and the
two it withdrew were flagged in place.

A patch covers what an edition *added*. It cannot cover what an edition
*changed*, and 2025 changes a field on 316 of the 2,334 UN numbers the two share.
The sharpest of them is UN 3423 tetramethylammonium hydroxide, solid: class 8 in
2023 and class 6.1 in 2025, with different labels, a different transport
category and hazard number 668 in place of 80. Anyone consigning it was given a
class the current ADR does not agree with, and nothing said so.

So the table is now read out of the official Dutch edition by
`scripts/extract_adr_table_a.py`, and the checks below are of two kinds.

**That the reading is sound.** The eleven rows of v1.52.0 were transcribed by
hand, off the page, into `adr_2025_additions.json`. That file has stopped being
the application's source and become something better: a hand-made reading of the
hardest rows in the book to compare a machine-made one against. Where the two
agree, two different methods on the same page agree.

**That the change reached the application.** A table nobody reads is not an
improvement, and the fields that moved are exactly the ones the compliance
checks compute with.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.dg.database import (
    forbidden_un_numbers,
    get_un_entries,
    is_transport_forbidden,
    withdrawn_un_numbers,
)

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg"


@pytest.fixture(scope="module")
def table():
    return json.loads((SEED / "adr_table_a.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_hand():
    return json.loads((SEED / "adr_2025_additions.json").read_text(encoding="utf-8"))


# --- the reading ------------------------------------------------------------

def test_the_seed_says_which_edition_and_which_documents(table):
    assert table["edition"] == "ADR 2025"
    assert "Dutch edition" in table["source"]
    assert "alphabetical index" in table["source"]


def test_no_page_of_the_book_was_left_unread(table):
    """A page the reader could not lay out is a hole with no bottom to it.

    Every UN number on it would be missing, and a missing UN number looks
    exactly like one the ADR does not carry.
    """
    assert table["summary"]["unreadable_pages"] == 0
    assert table["summary"]["un_numbers"] == 2345
    assert table["summary"]["rows"] == 3158


@pytest.mark.parametrize("field", [
    "classification_code", "packing_group", "labels", "special_provisions",
    "limited_quantity", "excepted_quantity", "packing_instructions",
    "carriage_packages", "carriage_bulk", "carriage_loading",
    "carriage_operation", "hazard_number", "tunnel_code",
])
def test_this_field_was_read_the_same_from_both_documents(table, field):
    """Table A and the alphabetical index are the same table, set twice.

    294 pages against 325, different column widths, different line breaks — so
    a column that has shifted in one reading has not shifted in the other. These
    thirteen agree on every one of the 2,345 UN numbers.
    """
    result = table["cross_check"]["fields"][field]
    assert result["agreement"] == 1.0, result["examples"][:3]


@pytest.mark.parametrize("field", ["class", "transport_category"])
def test_this_field_agrees_on_all_but_eight(table, field):
    """The two that are not perfect, held to what they actually are.

    The eight are named rather than rounded away. For the transport category
    they are every iodine entry — JOODWATERSTOFZUUR through JOODMONOCHLORIDE —
    which is the alphabetical index failing over one run of its own pages, not
    the table. For the class they are rows whose cell sat a hair outside its
    column; three of them were filled from the index, which is what a second
    reading is for.
    """
    result = table["cross_check"]["fields"][field]
    assert result["differs"] <= 8
    assert result["agreement"] >= 0.996


def test_the_hand_transcription_and_the_machine_agree(table, by_hand):
    """Two methods, one page.

    These eleven rows were read off the page by eye in v1.52.0, each one twice.
    They are the hardest in the book — new entries, unfamiliar names, several
    with no transport category at all — and they are the best available check on
    a reader that has to find its own column boundaries.
    """
    machine = {}
    for row in table["entries"]:
        machine.setdefault(row["un"], row)

    compared = 0
    for row in by_hand["entries"]:
        found = machine.get(str(row["un"]))
        assert found is not None, f"UN {row['un']} missing from the reading"
        for field in ("class", "classification_code", "packing_group",
                      "transport_category", "tunnel_code", "hazard_number"):
            if row.get(field, "") == "":
                continue
            assert found[field] == row[field], (
                f"UN {row['un']} {field}: by hand {row[field]!r}, "
                f"by machine {found[field]!r}")
            compared += 1
    assert compared > 30, "the comparison did not actually compare anything"


# --- what it changed for the application ------------------------------------

def test_tetramethylammonium_hydroxide_is_class_6_1():
    """The reclassification that was being answered with the 2023 class.

    Not a detail: the class decides the label, the transport category decides
    the 1.1.3.6 points factor, and the hazard identification number goes on the
    orange plate. All four were wrong.
    """
    rows = get_un_entries("3423")
    assert [r["class"] for r in rows] == ["6.1"]
    assert rows[0]["labels"] == "6.1, 8"
    assert rows[0]["transport_category"] == "1"
    assert rows[0]["hazard_number"] == "668"
    assert rows[0]["tunnel_code"] == "C/E"


def test_the_ammunition_rows_carry_their_own_subsidiary_hazard():
    """UN 0015 has three rows and the difference between them is the label.

    The 2023 export gave all three the same labels column, so the corrosive and
    the toxic variant lost their subsidiary hazard on the way to the document —
    silently, because nothing distinguished the rows to warn about.
    """
    labels = [row["labels"] for row in get_un_entries("0015")]
    assert labels == ["1", "1, 8", "1, 6.1"]


def test_the_added_entries_no_longer_need_a_patch():
    """Sodium-ion batteries come out of the road table itself now."""
    rows = get_un_entries("3551")
    assert len(rows) == 1
    assert rows[0]["transport_category"] == "2"
    assert rows[0]["tunnel_code"] == "E"
    assert rows[0]["name_nl"].startswith("NATRIUM-ION")
    # The English name has no road source at all — the edition read is Dutch and
    # the 2023 export never had the entry — so the sea code supplies it.
    assert rows[0]["name_en"]


def test_the_withdrawn_entries_are_the_difference_between_the_editions():
    """Derived, not listed. A list has to be remembered at the next edition."""
    assert withdrawn_un_numbers() == {"1499", "1999"}
    assert get_un_entries("1499")[0]["withdrawn_in"] == "ADR 2025"


def test_a_carriage_prohibition_is_not_read_out_of_an_empty_row():
    """The one thing the Dutch table cannot be asked.

    It writes a prohibition by leaving the row blank, and that is also how it
    writes "not subject to ADR". UN 1798 nitrohydrochloric acid may not be
    carried; UN 1845 dry ice travels freely; both are blank. Reading the absence
    would refuse the wrong one, so the prohibition comes from the export, which
    says it in words.
    """
    assert is_transport_forbidden("1798") is True
    assert is_transport_forbidden("1845") is False
    assert len(forbidden_un_numbers()) == 14


def test_the_aerosol_rows_are_in_the_order_the_adr_puts_them_in():
    """Which row comes first is not a detail for UN 1950.

    The export was sorted alphabetically by classification code, so the first
    row — the one filled in when the user has not said which — was 5A, the
    non-flammable aerosol. v1.51.0 measured what that costs: transport category
    3 where the ADR says 2, a points factor of 1 where it prescribes 3. Table A
    is in the ADR's own order and opens with 5F, the flammable spray can.
    """
    codes = [row["classification_code"] for row in get_un_entries("1950")]
    assert codes[0] == "5F"
    assert codes[:4] == ["5F", "5TF", "5FC", "5TFC"]
