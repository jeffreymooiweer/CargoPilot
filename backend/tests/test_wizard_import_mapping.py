"""The import has to say what it guessed.

The wizard reads `description | quantity | unit`. A spreadsheet from somebody
else rarely has those columns like that, and the import guessed silently: no
heading row recognised meant columns 0, 1 and 2. With a file starting with an
item number that yields references as descriptions and descriptions as
quantities, plus the heading row as a goods line. The user saw nothing of that
except `status=error` and 0 kg.

Guessing stays necessary — otherwise every import becomes handwork. What these
tests enforce is that the import says it was a guess, and passes along enough to
let that guess be corrected.
"""

import pytest

from app.services.wizard_import import SAMPLE_ROWS, analyse, apply_mapping

RECOGNISED = [
    ["Omschrijving", "Aantal", "Eenheid"],
    ["Stalen hoekprofiel 80x80x8x6000", "8", "stuks"],
]

# Four columns, not a single heading name the alias list knows, and an item
# number in front — the case this came apart on.
UNRECOGNISED = [
    ["Ref", "Benaming", "Aant.", "Eenh."],
    ["A-1", "Stalen hoekprofiel 80x80x8x6000", "8", "stuks"],
    ["A-2", "Balk HEA200 6000", "4", "stuks"],
]


def test_a_recognised_header_is_reported_as_recognised():
    result = analyse(RECOGNISED)
    assert result.source == "header"
    assert result.has_header
    assert result.mapping == {"description": 0, "quantity": 1, "unit": 2}


def test_an_unrecognised_header_is_reported_as_a_guess():
    """This is the whole point: the outcome is the same as before, but it now
    carries the label 'guessed' so the interface can ask further."""
    result = analyse(UNRECOGNISED)
    assert result.source == "position"
    assert not result.has_header
    assert result.mapping == {"description": 0, "quantity": 1, "unit": 2}


def test_the_guess_is_wrong_here_and_that_is_the_point():
    """What comes out without correction: references as descriptions and the
    heading row as a goods line."""
    result = analyse(UNRECOGNISED)
    text = apply_mapping(UNRECOGNISED, result.mapping, result.has_header)
    assert text.splitlines()[0] == "Ref | Benaming | Aant."
    assert "Stalen hoekprofiel" not in text.splitlines()[0]


def test_the_user_can_put_it_right():
    text = apply_mapping(
        UNRECOGNISED, {"description": 1, "quantity": 2, "unit": 3}, has_header=True
    )
    assert text.splitlines() == [
        "Stalen hoekprofiel 80x80x8x6000 | 8 | stuks",
        "Balk HEA200 6000 | 4 | stuks",
    ]


# --- What the interface needs to be able to ask that question ------------------

def test_every_column_comes_back_with_what_it_contains():
    """A dropdown saying 'column 1, column 2, column 3' helps nobody; what is in
    the column does.

    With an unrecognised heading row there is no heading name to show — row 1
    then counts as data — so the samples have to do the work. Whoever sees
    "Benaming, Stalen hoekprofiel 80x80x8x6000, Balk HEA200 6000" knows which
    column to pick.
    """
    columns = analyse(UNRECOGNISED).columns
    assert [c.index for c in columns] == [0, 1, 2, 3]
    assert columns[1].header == ""
    assert columns[1].samples == [
        "Benaming", "Stalen hoekprofiel 80x80x8x6000", "Balk HEA200 6000"
    ]


def test_the_header_row_is_not_offered_as_a_sample_value():
    """With a recognised heading row, row 1 is not data."""
    columns = analyse(RECOGNISED).columns
    assert columns[0].header == "Omschrijving"
    assert columns[0].samples == ["Stalen hoekprofiel 80x80x8x6000"]


def test_an_unrecognised_header_row_is_shown_as_data_because_that_is_what_it_is():
    """As long as the heading row is not recognised, row 1 counts as data — and
    seeing that is exactly what makes the user understand something is wrong."""
    columns = analyse(UNRECOGNISED).columns
    assert columns[0].header == ""
    assert columns[0].samples[0] == "Ref"


def test_only_a_handful_of_sample_values_travels():
    rows = [["x"] for _ in range(50)]
    assert len(analyse(rows).columns[0].samples) == SAMPLE_ROWS


def test_ragged_rows_do_not_lose_a_column():
    """Not every row is the same length; the widest determines how many columns
    there are."""
    rows = [["a", "1"], ["b", "2", "stuks"]]
    assert [c.index for c in analyse(rows).columns] == [0, 1, 2]


# --- Randgevallen --------------------------------------------------------------

def test_an_empty_file_yields_nothing_rather_than_a_guess():
    result = analyse([])
    assert result.source == "none"
    assert result.columns == []
    assert result.mapping == {"description": None, "quantity": None, "unit": None}


def test_a_row_without_a_description_is_left_out():
    """Such a line only produces an error line in the wizard."""
    rows = [["", "8", "stuks"], ["Balk HEA200 6000", "4", "stuks"]]
    text = apply_mapping(rows, {"description": 0, "quantity": 1, "unit": 2}, False)
    assert text == "Balk HEA200 6000 | 4 | stuks"


def test_a_mapping_that_points_past_the_row_yields_an_empty_cell():
    """A column the user picks but that is missing on this row must not fall over."""
    rows = [["Balk HEA200 6000", "4"]]
    text = apply_mapping(rows, {"description": 0, "quantity": 1, "unit": 9}, False)
    assert text == "Balk HEA200 6000 | 4"


@pytest.mark.parametrize("index", [None, -1])
def test_a_column_that_is_deliberately_left_unset_stays_empty(index):
    rows = [["Balk HEA200 6000", "4", "stuks"]]
    text = apply_mapping(rows, {"description": 0, "quantity": 1, "unit": index}, False)
    assert text == "Balk HEA200 6000 | 4"
