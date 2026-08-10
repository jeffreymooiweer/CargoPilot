"""The Dutch names had to come out of the book, because they exist nowhere else.

The Table A export this app was built on has an `name_en` and a `name_de` column
and no Dutch one. From that, four places in the repository concluded that the
ADR *has* no Dutch name. It has: the ADR is published in an official Dutch
edition and column (2) there reads BENZINE, ZOUTZUUR,
LITHIUM-ION-BATTERIJEN. There is no open data source for that column — it is
simply not on the internet — so it was read out of the book itself by
`scripts/extract_adr_names.py`.

That makes these tests something other than a formality. A machine reading of a
twenty-column table without column lines does not usually fall over; it shifts
by one and then two thousand substances quietly carry the wrong name. The
extraction guards against that itself, by reading the same data twice from two
independently typeset documents. What is checked here is the outcome: that the
seed still holds what was measured, that names known by hand are in it, and —
above all — that the names come out of the ADR and not out of a translation
machine. ZOUTZUUR is what the book says. A translator would have made
"WATERSTOFCHLORIDEOPLOSSING" of it, which is not a proper shipping name and
would be rejected at the border.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.services.dg.database import get_un_entries, search_un_numbers
from app.services.dg.names_nl import dutch_name, dutch_names, edition

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg" / "adr_names_nl.json"


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(SEED.read_text(encoding="utf-8"))


def test_the_seed_says_which_edition_it_was_read_from(payload):
    """Table A is renumbered every two years. A name file without an edition is
    a file nobody can check afterwards."""
    assert payload["edition"] == "ADR 2025"
    assert "tabel A" in payload["source"]
    assert edition() == "ADR 2025"


def test_the_reading_covers_the_whole_table(payload):
    """2,345 UN numbers, read from 294 pages. A drop in this number means the
    reading skipped pages — precisely the failure that leaves no trace of its
    own."""
    assert len(payload["names"]) == 2345
    assert payload["summary"]["table_rows"] == 3158


def test_the_two_readings_agreed_before_anything_was_written_down(payload):
    """Table A and the alphabetical index are two typesettings of the same data.
    Where they agree, the reading is right; the extraction refuses to write out
    below 0.99, and the figure it reached is recorded here."""
    assert payload["cross_check"]["index"]["agreement"] >= 0.99
    assert payload["cross_check"]["un_numbers"]["agreement"] >= 0.99


#: Names checked by hand against the printed page, with the page they stand on.
#: Deliberately spread over the classes and over the book, because a shifted
#: reading is usually only wrong from a certain page onwards.
BY_HAND = [
    ("1203", "BENZINE of MOTORBRANDSTOF"),
    ("1789", "ZOUTZUUR"),
    ("1090", "ACETON"),
    ("1993", "BRANDBARE VLOEISTOF, N.E.G."),
    ("3480", "LITHIUM-ION-BATTERIJEN (met inbegrip van lithium-ion-polymeer-batterijen)"),
    ("0004", "AMMONIUMPIKRAAT droog of bevochtigd met minder dan 10 massa-% water"),
]


def test_a_un_number_with_nine_rows_keeps_all_nine():
    """UN 1202 is diesel, gas oil and light heating oil, each once with a
    flashpoint up to 60 °C and once above it, plus three rows against EN 590.
    Nine rows in table A, nine names — an entry that collapses them puts a
    flashpoint on the document that was not measured."""
    names = dutch_names("1202")
    assert len(names) == 9
    assert names[0] == "DIESELOLIE (vlampunt ten hoogste 60°C)"
    assert "STOOKOLIE, LICHT" in names
    assert "DIESELOLIE overeenkomstig norm EN 590:2013 + A1:2017" in names


@pytest.mark.parametrize("un,expected", BY_HAND)
def test_names_read_by_hand_off_the_page(un, expected):
    assert dutch_name(un) == expected


def test_a_un_number_with_two_names_keeps_both():
    """Table A gives UN 1203 as BENZINE on one row and as MOTORBRANDSTOF on
    another, exactly as the English column joins its alternatives with "or".
    Dropping one of the two would put a name on the document that the consignor
    did not choose."""
    assert dutch_names("1203") == ["BENZINE", "MOTORBRANDSTOF"]


def test_the_un_number_may_be_written_any_way_round():
    assert dutch_name("un 1203") == dutch_name("1203") == dutch_name(1203)
    assert dutch_name("4") == dutch_name("0004")


def test_an_unknown_un_number_gives_nothing_rather_than_something(payload):
    assert dutch_names("9998") == []
    assert dutch_name("9998") == ""


# --- What separates a read name from a translated one ----------------------


def test_the_names_are_not_translations_of_the_english_ones():
    """A translation of "Gasoline" is not "BENZINE of MOTORBRANDSTOF", and a
    translation of "Hydrochloric acid" is not "ZOUTZUUR". These names carry
    wording that only the Dutch ADR has."""
    assert "MOTORBRANDSTOF" in dutch_name("1203")
    assert dutch_name("1789") == "ZOUTZUUR"
    # "massa-%" is the ADR's own notation; every machine translation writes
    # "gewichtsprocent" or "% by mass".
    assert "massa-%" in dutch_name("0004")


def test_the_wrapping_of_long_names_was_undone(payload):
    """A name that does not fit the column breaks after a hyphen, and the two
    halves have to close up again — "lithium-\nion-polymeer" is one word. A
    space left standing there is visible in every name with a hyphen in it,
    except where a conjunction follows: that is the hanging hyphen of the next
    test and it keeps its space."""
    broken = [f"UN {un}: {name}"
              for un, names in payload["names"].items()
              for name in names
              if re.search(r"[a-z]- (?!of\b|en\b|dan\b|noch\b)[a-z]", name)]
    assert broken == [], "\n".join(broken[:15])


def test_a_hanging_hyphen_kept_its_space():
    """The other side of the same rule: "verspreidings-, uitstoot- of
    voortdrijvende lading" is the ADR's own way of writing a shared suffix, and
    closing that up would make "uitstoot-of" of it."""
    assert "uitstoot- of voortdrijvende" in dutch_name("0009")


def test_no_name_ran_into_the_next_column(payload):
    """The class stands right up against the end of the name, and a reading that
    is one point too wide takes it with it: "met inerte kop" became "met inerte
    kop1". A lower-case word ending in a bare digit is the trace that leaves —
    "mengsel P2" and "mengsel F3" are the ADR's own gas mixtures and keep their
    capital, which is what separates the two."""
    trailing = [f"UN {un}: {name}"
                for un, names in payload["names"].items()
                for name in names
                if re.search(r"[a-z]\d$", name)]
    assert trailing == [], "\n".join(trailing[:15])


# --- What the app does with them -------------------------------------------


def test_the_entries_in_the_database_carry_their_dutch_name():
    entry = get_un_entries("1789")[0]
    assert entry["name_nl"] == "ZOUTZUUR"
    assert entry["name_en"].upper().startswith("HYDROCHLORIC")


def test_searching_on_a_dutch_name_finds_the_substance():
    """The reason for having them at all. Whoever typed "zoutzuur" got nothing:
    the search index held English and German only."""
    assert "1789" in {hit["un"] for hit in search_un_numbers("zoutzuur", 10)}
    assert "1203" in {hit["un"] for hit in search_un_numbers("benzine", 10)}
    assert "3480" in {hit["un"] for hit in search_un_numbers("lithium-ion", 10)}


def test_a_dutch_name_outranks_an_entry_that_merely_mentions_the_word():
    """UN 1789 *is* zoutzuur; UN 1798 is a mixture that has the word in its
    name. The first one has to come first."""
    hits = [hit["un"] for hit in search_un_numbers("zoutzuur", 10)]
    assert hits[0] == "1789"


def test_the_manifest_reports_the_name_file():
    """Two installations with the same manifest id compute with the same data;
    a seed outside the manifest breaks that promise."""
    from app.services.regulatory_manifest import build_manifest

    files = [dataset["file"]
             for rule_set in build_manifest()["rule_sets"]
             for dataset in rule_set["datasets"]]
    assert "adr_names_nl.json" in files
