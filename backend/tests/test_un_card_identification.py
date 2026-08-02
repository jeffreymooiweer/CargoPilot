"""Tests for reading the UN number out of a UN card.

The source files are numbered sequentially with no relation to their contents, so
every card has to be identified from what is printed on it. Filing a card under
the wrong UN number is worse than not filing it at all — a user would download
the emergency information for the wrong substance. These tests therefore focus on
the ways identification can go wrong: page numbers that look like UN numbers,
cards that mention other substances, and four-digit numbers that are not UN
numbers at all.
"""

import importlib.util
import sys
from pathlib import Path

import fitz
import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "fetch_un_cards.py"

spec = importlib.util.spec_from_file_location("fetch_un_cards", SCRIPT)
cards = importlib.util.module_from_spec(spec)
# @dataclass resolves its module through sys.modules, so register before exec.
sys.modules[spec.name] = cards
spec.loader.exec_module(cards)


@pytest.fixture(scope="module")
def database():
    return cards.load_un_database()


def make_card(heading: str, body: str = "", heading_size: float = 22.0) -> bytes:
    """A one-page PDF shaped like a UN card: a big heading and body text."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((60, 80), heading, fontsize=heading_size, fontname="helv")
    y = 160.0
    for line in body.split("\n"):
        page.insert_text((60, y), line, fontsize=9, fontname="helv")
        y += 14
    data = doc.tobytes()
    doc.close()
    return data


def test_reads_the_un_number_from_the_heading(database):
    data = make_card(
        "UN 1203  GASOLINE",
        "Class 3, packing group II.\nFlammable liquid. Keep away from heat.",
    )
    un, confidence, details = cards.identify(data, database)
    assert un == "1203"
    assert confidence == cards.CONFIRMED
    assert details["name_match"] >= 0.4


def test_confirms_through_the_shipping_name(database):
    """The name on the card must agree with the name in the database."""
    data = make_card("UN 2031", "NITRIC ACID, other than red fuming.\nClass 8 (5.1).")
    un, confidence, _details = cards.identify(data, database)
    assert un == "2031"
    assert confidence == cards.CONFIRMED


def test_page_numbers_do_not_become_un_numbers(database):
    """A bare four-digit number in body text must not win over the heading."""
    data = make_card(
        "UN 1017  CHLORINE",
        "Class 2.3. Toxic gas.\nDocument 2024 revision 1088, page 1090 of 3000.",
    )
    un, confidence, _details = cards.identify(data, database)
    assert un == "1017"
    assert confidence == cards.CONFIRMED


def test_a_card_mentioning_another_un_number_keeps_its_own(database):
    """Cross references in the body must not outrank the card's own heading."""
    data = make_card(
        "UN 1230  METHANOL",
        "Class 3 (6.1), packing group II.\n"
        "For mixtures see UN 1993. Not to be confused with UN 1170 ethanol.",
    )
    un, confidence, _details = cards.identify(data, database)
    assert un == "1230"
    assert confidence == cards.CONFIRMED


def test_a_four_digit_number_that_is_not_a_un_number_is_rejected(database):
    """9999 is not in the ADR table, so it must never be used as a filename."""
    data = make_card("Reference 9999", "Internal document. No substance data.")
    un, confidence, _details = cards.identify(data, database)
    assert un is None
    assert confidence in {cards.UNCERTAIN, cards.MISSING}


def test_a_scan_without_a_text_layer_is_reported_not_guessed(database):
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    data = doc.tobytes()
    doc.close()

    un, confidence, details = cards.identify(data, database)
    assert un is None
    assert confidence == cards.MISSING
    assert details["has_text_layer"] is False
    assert "scan" in str(details["note"])


def test_a_valid_number_without_a_matching_name_is_only_probable(database):
    """Enough to file, not enough to claim it was verified."""
    data = make_card("UN 1203", "Zie het veiligheidsinformatieblad van de leverancier.")
    un, confidence, _details = cards.identify(data, database)
    assert un == "1203"
    assert confidence == cards.PROBABLE


def test_the_database_covers_the_un_numbers_we_ship(database):
    # 2,928 ADR rows collapse to 2,336 unique UN numbers: several numbers have a
    # separate row per packing group.
    assert len(database) > 2300
    assert "1203" in database and "0004" in database
    assert cards.name_tokens(database["1203"].names[0])


@pytest.mark.parametrize("heading", ["UN1033", "UN-1033", "UN 1033", "un 1033"])
def test_prefix_spelling_variants(heading, database):
    un, _confidence, _details = cards.identify(make_card(heading, "Dimethyl ether."), database)
    assert un == "1033"


# The real cards are label/value pairs. This is the text layer of Cantell's
# part1.pdf, trimmed to the fields identification uses — heading, shipping name
# and the repeated footer.
REAL_CARD = """
UN number
0004
Shipping name
 AMMONIUM PICRATE
 AMMONIUMPICRAT
Class
1.1D
Packing group
–
Marine pollutant
Maybe
EmS
F-B, S-Y
UN 0004
IMDG - UN card
© Cantell 2023
UN 0004 AMMONIUM PICRATE
"""


def test_reads_the_number_from_the_un_number_field():
    labelled, footer, footers = cards.identify_from_labels(REAL_CARD)
    assert labelled == "0004"
    assert footer == "0004"
    assert footers == ["0004", "0004"]


def test_the_label_beats_any_other_number_on_the_card():
    """Class 1.1D, EmS codes and page furniture must not be mistaken for it."""
    text = REAL_CARD.replace("EmS\nF-B, S-Y", "EmS\nF-B, S-Y\nSee also UN 0027 and UN 1234")
    labelled, _footer, _footers = cards.identify_from_labels(text)
    assert labelled == "0004"


def test_a_card_whose_heading_and_footer_disagree_is_not_filed(database):
    """One of the two is wrong and we cannot tell which — so neither is used."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((60, 80), "UN number", fontsize=9, fontname="helv")
    page.insert_text((60, 95), "0004", fontsize=9, fontname="helv")
    page.insert_text((60, 700), "UN 0005 CARTRIDGES FOR WEAPONS", fontsize=8, fontname="helv")
    data = doc.tobytes()
    doc.close()

    un, confidence, details = cards.identify(data, database)
    assert details["labelled_un"] == "0004"
    assert details["footer_un"] == "0005"
    assert "footer" in str(details["note"])
    # Neither number is used: the card goes to _unidentified/ for a human.
    assert un is None
    assert confidence == cards.UNCERTAIN


def test_the_default_url_points_at_the_real_source():
    assert "{n}" in cards.DEFAULT_BASE_URL
    assert cards.DEFAULT_BASE_URL.startswith("https://")
