"""The what's-new card: release notes between the version seen and the version run.

An update to a self-hosted container is silent — the operator pulls a newer
image and the next login is a different program with nothing said. The card
closes that gap, and these tests hold its three parts to account:

* the parser reads ``CHANGELOG.md`` itself — the file a release is written
  into — so the card can never disagree with the record;
* the endpoint answers with the *running* version, not the newest heading,
  so a changelog ahead of or behind the binary cannot wedge the card open;
* the seen-marker is a user preference like any other: validated, stored in
  the JSON payload, absent in old payloads and therefore default-empty.
"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.settings import UserPreference
from app.models.user import User
from app.services import changelog, settings_store
from app.version import get_version


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    get_settings.cache_clear()

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, username="ada", email="ada@example.com", password_hash="x", role="user"))
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, 1)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- the parser, against the real record ------------------------------------


def test_the_real_changelog_parses_newest_first():
    entries = changelog.entries()
    assert len(entries) > 100
    assert entries[-1]["version"] == "1.0.0"
    versions = [tuple(int(p) for p in e["version"].split(".")) for e in entries]
    assert versions == sorted(versions, reverse=True)
    for entry in entries[:5]:
        assert entry["body"], entry["version"]
        assert len(entry["date"]) == 10


def test_the_newest_entry_is_the_version_being_released():
    """The release procedure writes the section before bumping goes out, so
    the file's first heading and the VERSION file must agree. If this fails,
    a release note was forgotten."""
    assert changelog.entries()[0]["version"] == get_version()


def test_since_filters_strictly_newer():
    entries = changelog.entries()
    second = entries[1]["version"]
    result = changelog.entries_since(second)
    assert [e["version"] for e in result["entries"]] == [entries[0]["version"]]
    assert result["truncated"] is False


def test_since_the_running_version_is_quiet():
    result = changelog.entries_since(changelog.entries()[0]["version"])
    assert result["entries"] == []
    assert result["truncated"] is False


def test_no_marker_gets_the_cap_and_says_it_was_cut():
    """159 releases is a history, not release notes. Empty and unparseable
    markers both get the cap's worth and the truncated flag."""
    for marker in ("", "not-a-version"):
        result = changelog.entries_since(marker)
        assert len(result["entries"]) == changelog.MAX_ENTRIES
        assert result["truncated"] is True


def test_the_parser_reads_a_file_not_a_memory(tmp_path, monkeypatch):
    """Ordering and body attribution proven on a crafted file, including the
    plain hyphen a hand-typed heading would use instead of the em dash."""
    crafted = tmp_path / "CHANGELOG.md"
    crafted.write_text(
        "# Changelog\n\npreamble is no entry\n\n"
        "## [2.1.0] — 2026-02-01\n\n### Added\n\n- the second thing\n\n"
        "## [2.0.0] - 2026-01-01\n\n- the first thing\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(changelog, "_CANDIDATES", [crafted])
    entries = changelog.entries()
    assert [e["version"] for e in entries] == ["2.1.0", "2.0.0"]
    assert "second thing" in entries[0]["body"]
    assert "first thing" in entries[1]["body"]
    assert "preamble" not in entries[0]["body"]


def test_a_store_without_the_file_answers_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(changelog, "_CANDIDATES", [tmp_path / "absent.md"])
    assert changelog.entries() == []
    assert changelog.entries_since("") == {"entries": [], "truncated": False}


# --- the endpoint ------------------------------------------------------------


def test_the_endpoint_reports_the_running_version(client):
    response = client.get("/api/changelog", params={"since": get_version()})
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == get_version()
    assert payload["entries"] == []


def test_the_endpoint_serves_the_entries_between(client):
    second = changelog.entries()[1]["version"]
    payload = client.get("/api/changelog", params={"since": second}).json()
    assert [e["version"] for e in payload["entries"]] == [get_version()]
    assert set(payload["entries"][0]) == {"version", "date", "body"}


def test_release_notes_are_behind_the_login():
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/changelog").status_code == 401


# --- the seen-marker ----------------------------------------------------------


def test_the_marker_travels_with_the_account(client, db):
    mine = client.get("/api/settings/me").json()
    assert mine["last_seen_version"] == ""
    mine["last_seen_version"] = get_version()
    saved = client.put("/api/settings/me", json=mine)
    assert saved.status_code == 200
    assert saved.json()["last_seen_version"] == get_version()
    assert client.get("/api/settings/me").json()["last_seen_version"] == get_version()


def test_the_marker_is_a_version_number_or_nothing(client):
    mine = client.get("/api/settings/me").json()
    mine["last_seen_version"] = "latest"
    assert client.put("/api/settings/me", json=mine).status_code == 422


def test_a_payload_from_before_the_marker_defaults_empty(db):
    """A database written by v1.124.0 lacks the key; the default fills in."""
    db.add(UserPreference(user_id=1, data_json=json.dumps({"theme": "dark"})))
    db.commit()
    preferences = settings_store.user_preferences(db, 1)
    assert preferences.last_seen_version == ""
    assert preferences.theme == "dark"
