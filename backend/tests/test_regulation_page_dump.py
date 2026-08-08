"""Een tabel is geen tekst, en de vinder zoekt tekst.

``locate`` kiest tussen alle plekken waar een artikelnummer voorkomt door te
tellen hoeveel letters erop volgen. Voor een bepaling van zinnen is dat de juiste
regel. Voor ADR 7.5.2.1 is het de verkeerde: dat artikel is vrijwel volledig een
raster van kruisjes met een nummer in de kantlijn, dus het scoort bijna nul en
verliest van elke kruisverwijzing elders in het deel. De vinder meldde
"not found" terwijl de bepaling er gewoon staat.

Vandaar ``--page``: als het nummer niet te vinden is, is de pagina dat wel. Wat
hier wordt vastgelegd is vooral wat er *niet* mag gebeuren — een reeks van
duizend pagina's in een runlog zetten, of een omgekeerde reeks stilzwijgend als
leeg behandelen.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "read_land_regulations", ROOT / "scripts" / "read_land_regulations.py"
)
reader = importlib.util.module_from_spec(SPEC)
# @dataclass looks its own module up in sys.modules; registering after the
# exec is too late and fails with an AttributeError that says nothing.
sys.modules[SPEC.name] = reader
SPEC.loader.exec_module(reader)


def test_a_single_page_is_a_range_of_one():
    assert reader.parse_pages("594") == [594]


def test_a_range_runs_inclusive():
    """600-606 is zeven pagina's, niet zes: wie een hoofdstuk opvraagt wil ook
    de laatste bladzijde ervan."""
    assert reader.parse_pages("600-606") == [600, 601, 602, 603, 604, 605, 606]


def test_surrounding_space_does_not_matter():
    assert reader.parse_pages("  594 ") == [594]


@pytest.mark.parametrize("spec", ["606-600", "0", "-3", "0-4"])
def test_a_range_that_makes_no_sense_is_refused(spec):
    with pytest.raises(ValueError):
        reader.parse_pages(spec)


def test_a_range_wider_than_a_chapter_is_refused():
    """De rem. Zonder deze grens zet één typefout het hele deel in de runlog en
    is er niets meer terug te lezen."""
    with pytest.raises(ValueError):
        reader.parse_pages("1-13")


def test_twelve_pages_is_still_allowed():
    assert len(reader.parse_pages("100-111")) == 12


@pytest.mark.parametrize("spec", ["banana", "", "1-", "1-2-3"])
def test_something_that_is_not_a_page_is_refused(spec):
    with pytest.raises(ValueError):
        reader.parse_pages(spec)


# --- Zoeken door een afbreekstreepje heen --------------------------------
#
# RID breekt woorden af aan het regeleinde. Een zoekopdracht op "alkaline earth
# metal nitrates" leverde daardoor "no occurrence" op, en dat las als een
# uitspraak over de regelgeving terwijl het een uitspraak over de opmaak was.
# Voor een leesgereedschap is dat de ergste denkbare fout.


def test_a_word_broken_at_the_line_end_is_still_found():
    text = "articles of com-\npatibility group D may be loaded"
    haystack, _ = reader._searchable(text)
    needle, _ = reader._searchable("compatibility group D")
    assert needle in haystack


def test_the_position_points_back_into_the_real_text():
    """Het fragment dat wordt afgedrukt moet het echte fragment zijn, met
    afbreekstreepje en al — anders citeer je iets wat er niet staat."""
    text = "zie divi-\nsion 1.1 hierna"
    haystack, origin = reader._searchable(text)
    needle, _ = reader._searchable("division")
    start = origin[haystack.index(needle)]
    assert text[start:].startswith("divi-")


def test_case_and_stray_spacing_do_not_matter():
    haystack, _ = reader._searchable("ALKALI   metal\n  NITRATES")
    needle, _ = reader._searchable("alkali metal nitrates")
    assert needle in haystack


def test_a_genuine_hyphen_is_dropped_on_both_sides():
    """"self-reactive" wordt "selfreactive", en de zoekterm ook. Zolang beide
    kanten dezelfde behandeling krijgen, blijft de zoekterm werken."""
    haystack, _ = reader._searchable("self-reactive substances")
    needle, _ = reader._searchable("self-reactive")
    assert needle in haystack


def test_a_hyphen_between_words_does_not_glue_a_sentence_together():
    """Het streepje verdwijnt, maar een gedachtestreepje mag geen twee woorden
    aan elkaar plakken die in de tekst los staan."""
    haystack, _ = reader._searchable("klasse 5.1 - zie hierna")
    assert "5.1 zie hierna" in haystack


def test_the_finder_actually_uses_it():
    source = (ROOT / "scripts" / "read_land_regulations.py").read_text(encoding="utf-8")
    finder = source[source.index("def find("):]
    assert "_searchable" in finder[: finder.index("\ndef ")]


def test_the_dump_is_reachable_from_the_command_line():
    """De optie bestaat pas echt als main hem doorgeeft; een functie zonder vlag
    is precies het soort naad waar het eerder op misging."""
    source = (ROOT / "scripts" / "read_land_regulations.py").read_text(encoding="utf-8")
    assert '"--page"' in source
    assert "dump(doc, number)" in source


def test_the_workflow_offers_it_too():
    workflow = (ROOT / ".github" / "workflows" / "read-land-regulations.yml").read_text(
        encoding="utf-8"
    )
    assert "--page" in workflow
