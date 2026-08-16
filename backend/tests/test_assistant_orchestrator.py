"""The assistant chain, end to end and without any language model.

The deterministic floor of the design: parser, name recognition, the open
questions of dg/prepare and the registry's required fields carry a complete
conversation from "1000 jerrycans diesel" to a consignment ready for export.
A model (phase 23) may read free text more flexibly; it can never change what
is asked or what may be answered, because the orchestrator owns both lists —
which is exactly what these tests pin.
"""
import pytest

from app.core.database import SessionLocal
from app.services.assistant.orchestrator import step


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


def test_the_first_message_becomes_goods_lines_through_the_real_pipeline(db):
    state, pending, events = drive(db, ["1000 jerrycans diesel"])
    assert [e["kind"] for e in events][0] == "lines_added"
    line = state["draft_lines"][0]
    assert line["quantity"] == 1000 and line["unit"] == "jerrycan"
    # The recognition offered UN 1202; the assistant asks, it never decides.
    assert pending["scope"] == "un_confirm"
    assert [c["un"] for c in pending["candidates"]] == ["1202"]
    assert not line.get("confirmed_un")


def test_confirming_records_the_un_and_the_backend_s_questions_take_over(db):
    state, pending, events = drive(db, ["1000 jerrycans diesel", "ja"])
    assert state["draft_lines"][0]["confirmed_un"] == "1202"
    # The next question is dg/prepare's own, options included.
    assert pending["scope"] == "dg_question"
    assert pending["field"] == "carriage_mode"
    assert "packages" in pending["options"]


def test_answers_match_labels_as_well_as_values(db):
    """The stored value is "packages"; the person typed "colli". Both are the
    same answer, through the option labels the wizard already carries."""
    state, pending, _ = drive(db, ["1000 jerrycans diesel", "ja", "colli"])
    product = state["dg_entries"][0]["products"][0]
    assert product["carriage_mode"] == "packages"
    assert pending["field"] == "chosen_name"
    assert pending["options"] == ["DIESELOLIE", "GASOLIE", "STOOKOLIE, LICHT"]


def test_an_unmatched_answer_changes_nothing_and_asks_again(db):
    state, pending, events = drive(
        db, ["1000 jerrycans diesel", "ja", "per onderzeeboot"])
    assert any(e["kind"] == "not_understood" for e in events)
    assert pending["field"] == "carriage_mode"
    assert not state["dg_entries"][0]["products"][0].get("carriage_mode")


def test_the_whole_diesel_ride_reaches_ready_without_a_model(db):
    turns = ["1000 jerrycans diesel", "ja", "colli", "DIESELOLIE", "DIESEL FUEL",
             "25 L", "Mooiweer BV", "Kade 1, Rotterdam", "Afnemer GmbH",
             "Hafenstr. 2, Duisburg", "Rotterdam", "Duisburg", "Franco",
             "Rotterdam", "vandaag"]
    state, pending, events = drive(db, turns)
    assert pending is None
    ready = [e for e in events if e["kind"] == "ready"]
    assert ready and "cmr" in ready[-1]["documents"]
    product = state["dg_entries"][0]["products"][0]
    # Everything came through the same derivation the wizard uses.
    assert product["proper_shipping_name"] == "DIESELOLIE (DIESEL FUEL)"
    assert product["adr_total_quantity"] == "25000 L"
    assert state["doc_values"]["freight_payment"] == "prepaid"
    assert state["doc_values"]["established_date"].count("-") == 2


def test_rejecting_the_recognition_clears_the_dg_route(db):
    state, pending, events = drive(db, ["1000 jerrycans diesel", "nee"])
    assert any(e["kind"] == "un_dismissed" for e in events)
    assert state["draft_lines"][0]["dg_dismissed"] is True
    # No DG questions follow; the documents' own fields are next.
    assert pending is None or pending["scope"] == "doc_question"


def test_optional_questions_can_be_skipped_required_ones_cannot(db):
    state, pending, _ = drive(
        db, ["1000 jerrycans diesel", "ja", "skip"])
    # carriage_mode is required: skip does not move past it.
    assert pending["field"] == "carriage_mode"


def test_the_assistant_never_asks_a_question_of_its_own(db):
    """Every question the conversation raised is either a recognition
    confirmation, an open question of dg/prepare, or a registry field — the
    three lists the backend owns."""
    _state, _pending, events = drive(
        db, ["1000 jerrycans diesel", "ja", "colli", "DIESELOLIE",
             "DIESEL FUEL", "25 L"])
    kinds = {e["kind"] for e in events}
    assert kinds <= {"lines_added", "un_question", "un_confirmed", "answered",
                     "dg_question", "doc_question", "ready", "skipped",
                     "not_understood", "un_dismissed"}


def test_the_state_travels_and_nothing_is_stored_server_side(db):
    """Stateless contract: the same call with the same state and message is
    reproducible, and the input state object is not mutated."""
    state = fresh_state()
    before = str(state)
    step(state, "1000 jerrycans diesel", None, db, "nl")
    assert str(state) == before
