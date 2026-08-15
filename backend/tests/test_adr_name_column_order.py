"""The order of two fragments of one printed line in table A.

Column (1) holds the UN number and column (2) the name, and on the page they
are one line: "1108" on the left, "1-PENTENE (n-AMYLENE)" beside it. The reader
splits rows at a line that opens with four digits, so which of the two arrives
first decides whether the row exists at all.

Sorting the lines as `(y, text, edge)` ordered them by what they *say* whenever
they shared a y. That is right by accident for most of the table — a four-digit
number sorts before a capital — and wrong for every name that opens with a
locant, because "-" is 0x2D and "," is 0x2C while "1" is 0x31. Two entries were
damaged by each such name: the one that lost its name and vanished, and the one
above it that kept the stray name.

There is no PDF here — the volumes are not ours to redistribute — so these
tests run on the coordinates the reader would have handed the sorter. What they
record is the typesetting, not the content of the ADR.
"""
import importlib.util
import sys
from pathlib import Path

_PATH = (Path(__file__).resolve().parents[2] / "scripts"
         / "extract_adr_names_multilingual.py")
_spec = importlib.util.spec_from_file_location(
    "extract_adr_names_multilingual", _PATH)
reader = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = reader
_spec.loader.exec_module(reader)


#: (y, left x, text, right edge) — a UN number at x 57.5 and a name at x 100,
#: which is where the UNECE volume sets them.
def row(y, number, name):
    return [(y, 57.5, number, 75.0), (y, 100.0, name, 191.0)]


def texts(placed):
    return [text for _y, text, _edge in reader.order_lines(placed)]


def test_the_number_comes_before_a_name_that_starts_with_a_letter():
    """The case that always worked, kept so the fix cannot break it."""
    assert texts(row(283.0, "1107", "AMYL CHLORIDE")) == [
        "1107", "AMYL CHLORIDE"]


def test_the_number_comes_before_a_name_that_starts_with_a_locant():
    """UN 1108 on printed page 340 of the English volume. Sorted on the text,
    "1-PENTENE (n-AMYLENE)" comes first and the row is attached to UN 1107."""
    assert texts(row(308.5, "1108", "1-PENTENE (n-AMYLENE)")) == [
        "1108", "1-PENTENE (n-AMYLENE)"]


def test_a_comma_in_the_locant_does_not_move_the_name_either():
    """UN 1150, "1,2-DICHLOROETHYLENE": the comma is 0x2C, lower still."""
    assert texts(row(436.3, "1150", "1,2-DICHLOROETHYLENE")) == [
        "1150", "1,2-DICHLOROETHYLENE"]


def test_rows_stay_in_the_order_the_page_sets_them():
    """Top to bottom first, left to right within a line — and nothing else."""
    placed = (row(436.3, "1150", "1,2-DICHLOROETHYLENE")
              + row(461.9, "1152", "DICHLOROPENTANES")
              + row(283.0, "1107", "AMYL CHLORIDE"))
    assert texts(placed) == [
        "1107", "AMYL CHLORIDE",
        "1150", "1,2-DICHLOROETHYLENE",
        "1152", "DICHLOROPENTANES",
    ]


def test_a_wrapped_name_keeps_its_lines_under_the_first():
    """A name across several lines has no number beside the later ones, and
    those lines must not float up to the row above."""
    placed = (row(129.6, "1139", "COATING SOLUTION (includes")
              + [(138.1, 100.0, "surface treatments or coatings used", 191.0),
                 (146.6, 100.0, "for industrial or other purposes", 191.0)]
              + row(163.7, "1143", "CROTONALDEHYDE"))
    assert texts(placed) == [
        "1139", "COATING SOLUTION (includes",
        "surface treatments or coatings used",
        "for industrial or other purposes",
        "1143", "CROTONALDEHYDE",
    ]


def test_the_splitter_then_gives_the_row_its_own_name():
    """The point of the order, end to end: with the number first, the row
    splitter opens a band at it and the name lands inside that band."""
    placed = (row(283.0, "1107", "AMYL CHLORIDE")
              + row(308.5, "1108", "1-PENTENE (n-AMYLENE)"))
    bands = reader.split_bands(
        reader.order_lines(placed), reader.BY_UN_NUMBER, reader.ROW_GAP)
    assert [[text for text, _edge in band] for band, _y in bands] == [
        ["1107", "AMYL CHLORIDE"],
        ["1108", "1-PENTENE (n-AMYLENE)"],
    ]
