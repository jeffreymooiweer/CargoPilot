"""De import moet zeggen wat hij geraden heeft.

De wizard leest `omschrijving | aantal | eenheid`. Een spreadsheet van iemand
anders heeft die kolommen zelden zo, en de import raadde stilzwijgend: geen
koptekst herkend betekende kolom 0, 1 en 2. Bij een bestand dat begint met een
artikelnummer levert dat referenties als omschrijving en omschrijvingen als
aantal, plus de kopregel als goederenregel. De gebruiker zag daar niets van
terug behalve `status=error` en 0 kg.

Raden blijft nodig — anders wordt elke import handwerk. Wat deze tests
afdwingen is dat de import erbij zegt dat het een gok was, en genoeg meelevert
om die gok te laten corrigeren.
"""

import pytest

from app.services.wizard_import import SAMPLE_ROWS, analyse, apply_mapping

RECOGNISED = [
    ["Omschrijving", "Aantal", "Eenheid"],
    ["Stalen hoekprofiel 80x80x8x6000", "8", "stuks"],
]

# Vier kolommen, geen enkele kopnaam die de aliaslijst kent, en een
# artikelnummer vooraan — het geval waarop dit stukliep.
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
    """Dit is het hele punt: de uitkomst is dezelfde als vroeger, maar zij
    draagt nu het etiket 'geraden' zodat de interface kan doorvragen."""
    result = analyse(UNRECOGNISED)
    assert result.source == "position"
    assert not result.has_header
    assert result.mapping == {"description": 0, "quantity": 1, "unit": 2}


def test_the_guess_is_wrong_here_and_that_is_the_point():
    """Wat er zonder correctie uit komt: referenties als omschrijving en de
    kopregel als goederenregel."""
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


# --- Wat de interface nodig heeft om die vraag te kunnen stellen ---------------

def test_every_column_comes_back_with_what_it_contains():
    """Een keuzelijst met 'kolom 1, kolom 2, kolom 3' helpt niemand; wat er in
    de kolom staat wel.

    Bij een niet-herkende koptekst is er geen kopnaam om te tonen — regel 1
    telt dan als gegeven — dus de voorbeelden moeten het werk doen. Wie
    "Benaming, Stalen hoekprofiel 80x80x8x6000, Balk HEA200 6000" ziet staan,
    weet welke kolom hij moet kiezen.
    """
    columns = analyse(UNRECOGNISED).columns
    assert [c.index for c in columns] == [0, 1, 2, 3]
    assert columns[1].header == ""
    assert columns[1].samples == [
        "Benaming", "Stalen hoekprofiel 80x80x8x6000", "Balk HEA200 6000"
    ]


def test_the_header_row_is_not_offered_as_a_sample_value():
    """Bij een herkende koptekst is regel 1 geen gegeven."""
    columns = analyse(RECOGNISED).columns
    assert columns[0].header == "Omschrijving"
    assert columns[0].samples == ["Stalen hoekprofiel 80x80x8x6000"]


def test_an_unrecognised_header_row_is_shown_as_data_because_that_is_what_it_is():
    """Zolang de koptekst niet is herkend telt regel 1 als gegeven — en dat
    zien is juist wat de gebruiker doet begrijpen dat er iets misgaat."""
    columns = analyse(UNRECOGNISED).columns
    assert columns[0].header == ""
    assert columns[0].samples[0] == "Ref"


def test_only_a_handful_of_sample_values_travels():
    rows = [["x"] for _ in range(50)]
    assert len(analyse(rows).columns[0].samples) == SAMPLE_ROWS


def test_ragged_rows_do_not_lose_a_column():
    """Niet elke rij is even lang; de breedste bepaalt hoeveel kolommen er zijn."""
    rows = [["a", "1"], ["b", "2", "stuks"]]
    assert [c.index for c in analyse(rows).columns] == [0, 1, 2]


# --- Randgevallen --------------------------------------------------------------

def test_an_empty_file_yields_nothing_rather_than_a_guess():
    result = analyse([])
    assert result.source == "none"
    assert result.columns == []
    assert result.mapping == {"description": None, "quantity": None, "unit": None}


def test_a_row_without_a_description_is_left_out():
    """Zo'n regel levert in de wizard alleen een foutregel op."""
    rows = [["", "8", "stuks"], ["Balk HEA200 6000", "4", "stuks"]]
    text = apply_mapping(rows, {"description": 0, "quantity": 1, "unit": 2}, False)
    assert text == "Balk HEA200 6000 | 4 | stuks"


def test_a_mapping_that_points_past_the_row_yields_an_empty_cell():
    """Een kolom die de gebruiker kiest maar die op deze regel ontbreekt mag
    niet omvallen."""
    rows = [["Balk HEA200 6000", "4"]]
    text = apply_mapping(rows, {"description": 0, "quantity": 1, "unit": 9}, False)
    assert text == "Balk HEA200 6000 | 4"


@pytest.mark.parametrize("index", [None, -1])
def test_a_column_that_is_deliberately_left_unset_stays_empty(index):
    rows = [["Balk HEA200 6000", "4", "stuks"]]
    text = apply_mapping(rows, {"description": 0, "quantity": 1, "unit": index}, False)
    assert text == "Balk HEA200 6000 | 4"
