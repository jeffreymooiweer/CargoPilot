"""Recognition of dangerous goods by name, as a suggestion.

Typing "benzine" on the lines step used to produce nothing: only a literal
"UN 1203" was recognised, while the four-language name index had known the
substance all along. These tests pin the boundary of the new recognition: the
capital-printed name of the book matches, nothing shorter does, and the result
is a candidate list for the user to confirm — never a silent classification.
"""
import pytest

from app.core.database import SessionLocal
from app.services.dg.name_detection import detect_name_candidates
from app.services.pipeline import parse_and_calculate


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def uns(text, language="nl"):
    return [c["un"] for c in detect_name_candidates(text, language)]


def test_the_user_s_own_example_petrol_by_its_dutch_name():
    assert uns("benzine") == ["1203"]
    assert uns("20 vaten benzine") == ["1203"]


def test_the_candidate_carries_what_the_chip_shows():
    (candidate,) = detect_name_candidates("benzine")
    assert candidate["un"] == "1203"
    assert candidate["class"] == "3"
    assert "BENZINE" in candidate["name"]


def test_a_compound_word_is_not_the_substance():
    """A petrol engine is a machine, not a consignment of petrol."""
    assert uns("benzinemotor") == []
    assert uns("aanhanger met benzinemotor") == []


def test_a_qualified_name_matches_only_as_the_book_prints_it():
    """ALUMINIUM, GESMOLTEN is capital-printed as a whole, so a plain
    aluminium tube raises no suggestion."""
    assert uns("aluminium buis 50x50") == []


def test_ambiguity_yields_candidates_not_an_answer():
    """Two sulphuric acids differ in the qualifier the book prints in lower
    case; the recognition offers both and decides neither."""
    found = uns("3 IBC zwavelzuur")
    assert "1830" in found and "2796" in found


def test_all_four_languages_reach_the_same_substance():
    for text, language in (
        ("benzine", "nl"),
        ("gasoline", "en"),
        ("petrol", "en"),
        ("Benzin", "de"),
        ("essence", "fr"),
    ):
        assert uns(text, language) == ["1203"], text


def test_case_and_accents_do_not_matter():
    assert uns("SCHWEFELSÄURE") == uns("schwefelsaure")


def test_plain_steel_lines_stay_quiet():
    for text in ("stalen buis 50x50x3", "HEA 200 balk 12m", "plaat 2000x1000x5"):
        assert uns(text) == [], text


def test_an_explicit_un_number_leaves_nothing_to_suggest(db):
    result = parse_and_calculate("UN 1203 benzine | 10 | vaten", db)
    line = result["lines"][0]
    assert line["dangerous_goods"] is True
    assert line["dg_name_candidates"] == []


def test_the_word_at_the_pump_reaches_its_substance():
    """"diesel" is not a name the book prints — "DIESELOLIE", "DIESEL FUEL" —
    but it is the exact first word of one and a near-complete single-word
    name of the other. The fallback match closes that gap without opening
    the compound-word door: "benzinemotor" still matches nothing."""
    assert uns("diesel") == ["1202"]
    assert uns("20 vaten diesel") == ["1202"]
    assert uns("gasolie") == ["1202"]
    assert uns("benzinemotor") == []
    for text in ("stalen buis 50x50x3", "plaat 2000x1000x5", "aluminium buis"):
        assert uns(text) == [], text


def test_the_pipeline_carries_the_candidates_without_deciding(db):
    result = parse_and_calculate("benzine | 10 | vaten", db)
    line = result["lines"][0]
    # The suggestion is there for the interface —
    assert [c["un"] for c in line["dg_name_candidates"]] == ["1203"]
    # — and the classification was NOT set on the strength of it.
    assert line["dangerous_goods"] is False
