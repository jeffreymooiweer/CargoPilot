"""The goods themselves, not only the dangerous ones.

Owner feedback on v1.107.0, in two measured defects. "1000 jerricans of petrol
and a pallet of sand-lime brick" became *one* line — description "petrol and a
pallet of sand-lime brick", 1000 jerricans — so the second consignment
silently disappeared. And "4 pallets of sand-lime brick" was carried from the
first sentence to the consignor's name without a single question, while the
pipeline had already reported "dimensions_missing" and the catalogue already
held the density: one question turns that line into 6144 kg and 3.84 m³.

A third thing was free all along: since v1.107.0 the content of one package is
known, and a count of packages times that content is a volume the density
turns into a mass. 1000 jerricans of 25 litres of petrol is 18625 kg.
"""
import pytest

from app.core.database import SessionLocal
from app.services.assistant.goods import parse_dimensions, parse_weight_kg
from app.services.assistant.orchestrator import _split_segments, step


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def fresh_state():
    return {"modality": "road", "draft_lines": [], "dg_entries": [], "doc_values": {}}


def drive(db, turns, state=None, pending=None):
    events = []
    state = state or fresh_state()
    for message in turns:
        result = step(state, message, pending, db, "nl")
        state, pending = result["state"], result["pending"]
        events.extend(result["events"])
    return state, pending, events


# --- splitting a spoken sentence into the goods it names --------------------

def test_two_goods_in_one_sentence_become_two_lines(db):
    state, _pending, _events = drive(
        db, ["1000 jerrycans benzine en een pallet kalkzandsteen"])
    lines = state["draft_lines"]
    assert [(line["description"], line["quantity"], line["unit"]) for line in lines] == [
        ("benzine", 1000.0, "jerrycan"),
        ("kalkzandsteen", 1.0, "pallet"),
    ]


def test_a_list_of_three_becomes_three_lines(db):
    state, _pending, _events = drive(
        db, ["1000 jerrycans diesel, 4 pallets kalkzandsteen en "
             "8 stuks staal hoekprofiel 80x80x8x6000"])
    assert [line["description"] for line in state["draft_lines"]] == [
        "diesel", "kalkzandsteen", "staal hoekprofiel 80x80x8x6000"]


def test_the_content_of_a_package_is_never_mistaken_for_a_second_item():
    """"of 25 l with petrol" and "at 200 litres each" belong to the item they
    are written on; only a separating word before a count, a known unit and a
    description after it starts a new one."""
    assert _split_segments("1000 jerrycans van 25l met benzine") == [
        "1000 jerrycans van 25l met benzine"]
    assert _split_segments("10 vaten à 200 liter dieselolie") == [
        "10 vaten à 200 liter dieselolie"]
    # A weight quality after a comma is not a consignment of its own.
    assert _split_segments("10 dozen A4-papier, 80 grams") == [
        "10 dozen A4-papier, 80 grams"]
    # And a sentence without counts stays exactly as it was said.
    assert _split_segments("benzine en diesel") == ["benzine en diesel"]


# --- what the goods leave open ---------------------------------------------

def test_a_pallet_of_bricks_is_asked_for_its_dimensions(db):
    state, pending, _events = drive(db, ["4 pallets kalkzandstenen"])
    assert pending["scope"] == "goods_question"
    assert pending["field"] == "goods_dimensions"
    assert pending["required"] is False
    assert pending["reason"] == "dimensions_complete_the_picture"
    assert pending["goods"] == "kalkzandstenen"
    assert "120 x 80 x 100" in pending["simple"]["nl"]
    assert state["draft_lines"][0]["weight_total_kg"] is None


def test_the_answer_turns_the_line_into_a_weight_and_a_volume(db):
    state, pending, _events = drive(
        db, ["4 pallets kalkzandstenen", "120 x 80 x 100 cm"])
    line = state["draft_lines"][0]
    assert (line["length_cm"], line["width_cm"], line["height_cm"]) == (120.0, 80.0, 100.0)
    assert line["weight_total_kg"] == 6144.0
    assert line["transport_volume_m3"] == 3.84
    # The question is gone the next turn, because nothing is missing any more.
    assert pending["scope"] == "doc_question"


def test_metres_and_spoken_separators_are_understood(db):
    state, _pending, _events = drive(
        db, ["4 pallets kalkzandstenen", "1,2 bij 0,8 bij 1 m"])
    line = state["draft_lines"][0]
    assert (line["length_cm"], line["width_cm"], line["height_cm"]) == (120.0, 80.0, 100.0)


def test_an_unreadable_measurement_is_asked_again_and_writes_nothing(db):
    state, pending, events = drive(
        db, ["4 pallets kalkzandstenen", "weet ik niet precies"])
    clarify = [e for e in events if e["kind"] == "clarify"]
    assert clarify and clarify[-1]["example"] == "120 x 80 x 100 cm"
    assert pending["field"] == "goods_dimensions"
    assert state["draft_lines"][0]["length_cm"] is None if "length_cm" in state["draft_lines"][0] \
        else "length_cm" not in state["draft_lines"][0]


def test_the_measurement_question_can_be_skipped(db):
    state, pending, _events = drive(
        db, ["4 pallets kalkzandstenen", "overslaan"])
    assert pending["scope"] == "doc_question"
    assert "goods:1:goods_dimensions" in state["skipped_questions"]


def test_steel_from_the_catalogue_is_asked_nothing(db):
    """The measurements are in the description and the profile is in the
    catalogue: the line is complete, so no question is raised."""
    state, pending, _events = drive(db, ["8 stuks staal hoekprofiel 80x80x8x6000"])
    line = state["draft_lines"][0]
    assert line["weight_total_kg"] == 458.19
    assert line["transport_volume_m3"] == 0.3072
    assert pending["scope"] == "doc_question"


# --- the content of a package as a weight ----------------------------------

def test_a_thousand_jerricans_of_petrol_weigh_what_the_density_says(db):
    state, _pending, _events = drive(
        db, ["1000 jerrycans van 25l met benzine"])
    line = state["draft_lines"][0]
    assert line["weight_total_kg"] == 18625.0
    assert line["material_volume_m3"] == 25.0
    # The packaging around the contents is not known, so the transport volume
    # stays open rather than claiming the volume of the liquid.
    assert line["transport_volume_m3"] is None


def test_a_computed_weight_never_travels_back_in_as_an_answer(db):
    """A weight per package rounded to 18.62 kg, fed in again as an override,
    turns 18625 kg of petrol into 18620. Derived values stay derived."""
    state, pending, _events = drive(db, ["1000 jerrycans van 25l met benzine"])
    for _ in range(3):
        state, pending, _events = drive(db, ["overslaan"], state, pending)
        if pending is None or pending["scope"] != "goods_question":
            break
    assert state["draft_lines"][0]["weight_total_kg"] == 18625.0


# --- reading an answer -----------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("120x80x100", (120.0, 80.0, 100.0)),
    ("120 x 80 x 100 cm", (120.0, 80.0, 100.0)),
    ("1,2 x 0,8 x 1 m", (120.0, 80.0, 100.0)),
    ("120 bij 80 bij 100", (120.0, 80.0, 100.0)),
    ("2000 x 1000 x 800 mm", (200.0, 100.0, 80.0)),
])
def test_measurements_are_read_the_way_people_write_them(text, expected):
    values = parse_dimensions(text)
    assert (values["length_cm"], values["width_cm"], values["height_cm"]) == expected


@pytest.mark.parametrize("text,expected", [
    ("900 kg", 900.0),
    ("900", 900.0),
    ("0,9 ton", 900.0),
    ("1.5 t", 1500.0),
])
def test_a_weight_is_read_with_or_without_its_unit(text, expected):
    assert parse_weight_kg(text) == expected


def test_nonsense_is_not_a_measurement_and_not_a_weight():
    assert parse_dimensions("geen idee") is None
    assert parse_weight_kg("geen idee") is None
    # Three measurements are not a weight, however they are phrased.
    assert parse_weight_kg("120 x 80 x 100 cm") is None
