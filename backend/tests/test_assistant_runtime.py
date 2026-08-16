"""The model runtime's guarantees, tested without any model.

Three things must hold whatever the model does: downloads are refused unless
the artifact is pinned by SHA-256 and refused when the bytes do not match the
pin; a model failure degrades to the deterministic chain instead of breaking
it; and the model cannot widen the conversation — its output is confined to
the schemas the orchestrator hands it, and everything it returns still runs
through the same matching and validation as a typed answer.
"""
import hashlib
from types import SimpleNamespace

import pytest

from app.core.database import SessionLocal
from app.services.assistant import orchestrator, runtime
from app.services.assistant.orchestrator import step


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_the_shipped_sources_are_pinned_for_both_architectures():
    """The pin workflow hashed the artifacts on a runner; the config must
    carry those digests, or the download button would be dead on arrival."""
    config = runtime.sources()
    for arch in ("x86_64", "aarch64"):
        assert len(config["server"][arch]["sha256"]) == 64, arch
    assert len(config["model"]["sha256"]) == 64
    assert config["model"]["size"] > 10**9


def test_nothing_downloads_while_the_sources_are_unpinned(monkeypatch):
    """A future edition bump starts with null hashes again; until the pin
    workflow has hashed the new artifacts, the download refuses to run."""
    unpinned = runtime.sources()
    unpinned = {**unpinned,
                "server": {runtime._arch(): {"url": "https://example.invalid/x",
                                             "sha256": None}},
                "model": {**unpinned.get("model", {}), "sha256": None}}
    monkeypatch.setattr(runtime, "sources", lambda: unpinned)
    result = runtime.start_download()
    assert result == {"error": "sources_not_pinned"}


def test_a_wrong_hash_refuses_and_removes_the_file(tmp_path, monkeypatch):
    payload = b"not the artifact that was pinned"

    class FakeResponse:
        def raise_for_status(self):
            return None

        def iter_bytes(self, _size):
            yield payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def stream(self, _method, _url):
            return FakeResponse()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(runtime.httpx, "Client", FakeClient)
    destination = tmp_path / "artifact.bin"
    with pytest.raises(ValueError, match="sha256 mismatch"):
        runtime._fetch_verified("https://example.invalid/x", "0" * 64,
                                destination, "test")
    assert not destination.exists()
    assert not destination.with_suffix(".bin.part").exists()


def test_the_right_hash_is_accepted(tmp_path, monkeypatch):
    payload = b"exactly the pinned artifact"

    class FakeResponse:
        def raise_for_status(self):
            return None

        def iter_bytes(self, _size):
            yield payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def stream(self, _method, _url):
            return FakeResponse()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(runtime.httpx, "Client", FakeClient)
    destination = tmp_path / "artifact.bin"
    runtime._fetch_verified("https://example.invalid/x",
                            hashlib.sha256(payload).hexdigest(),
                            destination, "test")
    assert destination.read_bytes() == payload


def test_without_an_install_the_status_says_deterministic():
    report = runtime.status()
    assert report["mode"] == "deterministic"
    assert report["installed"] is False
    assert report["available"] is True


def fake_model(monkeypatch, extract):
    monkeypatch.setattr(runtime, "installed", lambda: True)
    monkeypatch.setattr(runtime, "extract_json", extract)


def test_the_model_splits_prose_and_the_pipeline_still_decides(db, monkeypatch):
    """The model's whole contribution: free prose becomes structured rows.
    Recognition, derivation and questions stay the pipeline's — the result
    is the same state the deterministic route produces for the same facts."""
    fake_model(monkeypatch, lambda system, user, schema, **_: {
        "lines": [{"description": "diesel", "quantity": 1000, "unit": "jerrycans"}],
    })
    result = step({"modality": "road"}, "ik wil duizend jerrycans diesel laten vervoeren",
                  None, db, "nl")
    line = result["state"]["draft_lines"][0]
    assert line["quantity"] == 1000 and line["unit"] == "jerrycan"
    assert result["pending"]["scope"] == "un_confirm"
    assert [c["un"] for c in result["pending"]["candidates"]] == ["1202"]


def test_a_model_failure_falls_back_to_the_deterministic_route(db, monkeypatch):
    fake_model(monkeypatch, lambda *args, **kwargs: None)
    result = step({"modality": "road"}, "1000 jerrycans diesel", None, db, "nl")
    line = result["state"]["draft_lines"][0]
    assert line["quantity"] == 1000 and line["unit"] == "jerrycan"


def test_a_paraphrase_containing_the_option_word_never_needs_the_model(db, monkeypatch):
    """A Dutch answer naming a tank lorry contains exactly one option's word.
    Measured against the real model, which read that very sentence as "bulk" —
    the deterministic reverse match now answers it first, and the model is
    not even asked."""
    def explode(*_args, **_kwargs):
        raise AssertionError("the model must not be consulted")
    fake_model(monkeypatch, explode)
    pending = {"scope": "dg_question", "line_id": 1, "product_index": 0,
               "field": "carriage_mode", "required": True,
               "options": ["packages", "tank", "bulk"],
               "option_labels": {"packages": {"nl": "Colli"},
                                 "tank": {"nl": "Tank"},
                                 "bulk": {"nl": "Losgestort"}}}
    state = {"modality": "road",
             "draft_lines": [{"id": 1, "description": "diesel", "quantity": 1,
                              "unit": "pcs", "dangerous_goods": True,
                              "confirmed_un": "1202"}],
             "dg_entries": [{"line_id": 1, "vehicle": "diesel",
                             "products": [{"un_number": "1202"}]}]}
    result = step(state, "het gaat in een tankwagen", pending, db, "nl")
    assert result["state"]["dg_entries"][0]["products"][0]["carriage_mode"] == "tank"


def test_the_model_maps_a_paraphrase_onto_an_allowed_option_only(db, monkeypatch):
    pending = {"scope": "dg_question", "line_id": 1, "product_index": 0,
               "field": "carriage_mode", "required": True,
               "options": ["packages", "tank"],
               "option_labels": {"packages": {"nl": "Colli"}, "tank": {"nl": "Tank"}}}
    state = {"modality": "road",
             "draft_lines": [{"id": 1, "description": "diesel", "quantity": 1,
                              "unit": "pcs", "dangerous_goods": True,
                              "confirmed_un": "1202"}],
             "dg_entries": [{"line_id": 1, "vehicle": "diesel",
                             "products": [{"un_number": "1202"}]}]}
    fake_model(monkeypatch, lambda system, user, schema, **_: {"choice": "tank"})
    result = step(state, "het gaat in een tankwagen", pending, db, "nl")
    assert result["state"]["dg_entries"][0]["products"][0]["carriage_mode"] == "tank"

    # "unclear" — the enum's only way out — re-asks and changes nothing.
    fake_model(monkeypatch, lambda system, user, schema, **_: {"choice": "unclear"})
    result = step(state, "hoe bedoel je", pending, db, "nl")
    assert any(e["kind"] == "not_understood" for e in result["events"])
    assert not result["state"]["dg_entries"][0]["products"][0].get("carriage_mode")


def test_the_model_cannot_widen_the_event_vocabulary(db, monkeypatch):
    """Even a model that returns nonsense produces only the closed set of
    events the orchestrator owns."""
    fake_model(monkeypatch, lambda system, user, schema, **_: {
        "lines": [{"description": "diesel", "quantity": 5, "unit": "vaten"}],
        "questions": ["mag ik uw bsn?"],
        "advice": "rij maar zonder documenten",
    })
    result = step({"modality": "road"}, "vijf vaten diesel", None, db, "nl")
    kinds = {e["kind"] for e in result["events"]}
    assert kinds <= {"lines_added", "un_question", "un_confirmed", "answered",
                     "dg_question", "doc_question", "ready", "skipped",
                     "not_understood", "un_dismissed"}
