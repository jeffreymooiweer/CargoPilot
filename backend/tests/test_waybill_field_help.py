"""The consignment note explained at the field, the way the sVa booklet does.

The owner supplied "De vrachtbrief; goed geregeld" (sVa / Stichting
Vervoeradres, 2004), the box-by-box explanation of the CMR/AVC consignment
note, and asked for two things: the info marks on the CMR questions must
carry short versions of those texts, and the notify party had to be judged.
Judged it was: a notify party is a sea-carriage concept — the party the
shipping line informs when the cargo reaches the discharge port — and the
CMR has no such box. The field sat in the *shared* parties section without a
condition, so every road shipment was asked for it and no document printed
it. It now lives on the B/L shipping instructions alone.
"""
import pytest

from app.core.database import SessionLocal
from app.services.assistant.orchestrator import step
from app.services.documents.registry import get_registry


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def fields_of(doc: dict, registry: dict) -> list[dict]:
    shared = {s["key"]: s for s in registry["shared_sections"]}
    out: list[dict] = []
    for section in doc.get("sections", []):
        resolved = shared.get(section.get("ref")) if section.get("ref") else section
        out.extend(resolved.get("fields", []) or [])
    return out


def test_the_notify_party_belongs_to_sea_documents_only():
    registry = get_registry()
    for doc in registry["documents"]:
        keys = {f["key"] for f in fields_of(doc, registry)}
        if doc["key"] == "bl_si":
            assert "notify_party" in keys
        else:
            assert "notify_party" not in keys, doc["key"]
    # And the field explains itself: what a notify party is, and that the
    # CMR has none.
    bl = next(d for d in registry["documents"] if d["key"] == "bl_si")
    notify = next(f for f in fields_of(bl, registry) if f["key"] == "notify_party")
    assert "CMR" in notify["help"]["nl"]


def test_a_road_shipment_is_never_asked_for_a_notify_party(db):
    state = {"modality": "road", "draft_lines": [], "dg_entries": [], "doc_values": {}}
    pending = None
    asked: list[str] = []
    result = step(state, "4 pallets kalkzandstenen", pending, db, "nl")
    state, pending = result["state"], result["pending"]
    for _ in range(60):
        if pending is None:
            break
        asked.append(str(pending.get("field")))
        result = step(state, "overslaan" if pending.get("required") is False else "x",
                      pending, db, "nl")
        state, pending = result["state"], result["pending"]
    assert "notify_party" not in asked


def test_every_question_the_cmr_asks_carries_help_in_four_languages():
    """The info mark may never be empty: each field the survey can raise for
    the CMR carries the booklet's digest in all four languages."""
    registry = get_registry()
    cmr = next(d for d in registry["documents"] if d["key"] == "cmr")
    missing: list[str] = []
    for field in fields_of(cmr, registry):
        if field.get("status") not in ("USER_REQUIRED", "USER_OPTIONAL", "CONDITIONAL"):
            continue
        if field.get("auto_from") or field.get("type") == "checkbox":
            continue
        help_text = field.get("help") or {}
        for lang in ("nl", "en", "de", "fr"):
            if not str(help_text.get(lang) or "").strip():
                missing.append(f"{field['key']}:{lang}")
    assert missing == [], f"fields without help: {missing}"
