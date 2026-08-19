"""The update check: one outbound question, behind the administrator's switch.

A container cannot update itself, so all this feature may do is tell the one
person who operates it that there is something to pull. What these tests hold
it to:

* the switch is real — off means GitHub is never contacted, checked per
  request rather than once at startup, and a non-admin cannot trigger the
  call at all;
* not knowing is said as not knowing — an unreachable GitHub answers
  ``reachable: false``, never "you are up to date";
* the answer is cached, long when it worked and briefly when it did not, so
  an outage does not turn every settings visit into a timeout wait.
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.user import User
from app.services import updates
from app.version import get_version


@pytest.fixture(autouse=True)
def fresh_cache():
    updates.clear_cache()
    yield
    updates.clear_cache()


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
    session.add(User(id=1, username="ada", email="ada@example.com", password_hash="x", role="admin"))
    session.add(User(id=2, username="bob", email="bob@example.com", password_hash="x", role="user"))
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


def client_as(db, user_id: int) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, user_id)
    return TestClient(app)


@pytest.fixture
def admin_client(db):
    with client_as(db, 1) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def github_answers(monkeypatch, tag: str, calls: list | None = None):
    def fake_get(url, **kwargs):
        if calls is not None:
            calls.append(url)
        request = httpx.Request("GET", url)
        payload = {"tag_name": tag, "html_url": f"https://github.com/x/releases/{tag}"}
        return httpx.Response(200, request=request, content=json.dumps(payload))

    monkeypatch.setattr(updates.httpx, "get", fake_get)


def github_is_down(monkeypatch, calls: list | None = None):
    def fake_get(url, **kwargs):
        if calls is not None:
            calls.append(url)
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(updates.httpx, "get", fake_get)


# --- the service --------------------------------------------------------------


def test_a_release_tag_is_read_without_its_v(monkeypatch):
    github_answers(monkeypatch, "v9.9.9")
    release = updates.latest_release()
    assert release == {"version": "9.9.9", "url": "https://github.com/x/releases/v9.9.9"}


def test_a_tag_that_is_not_a_version_is_not_knowing(monkeypatch):
    github_answers(monkeypatch, "nightly")
    assert updates.latest_release() is None


def test_a_good_answer_is_asked_once(monkeypatch):
    calls: list = []
    github_answers(monkeypatch, "v9.9.9", calls)
    updates.latest_release()
    updates.latest_release()
    assert len(calls) == 1


def test_a_failure_is_not_retried_immediately(monkeypatch):
    calls: list = []
    github_is_down(monkeypatch, calls)
    assert updates.latest_release() is None
    assert updates.latest_release() is None
    assert len(calls) == 1


# --- the endpoint --------------------------------------------------------------


def test_a_newer_release_is_an_update(admin_client, monkeypatch):
    github_answers(monkeypatch, "v999.0.0")
    payload = admin_client.get("/api/update-status").json()
    assert payload["update_available"] is True
    assert payload["current"] == get_version()
    assert payload["latest"] == "999.0.0"
    assert payload["url"]


def test_the_running_release_is_no_update(admin_client, monkeypatch):
    github_answers(monkeypatch, f"v{get_version()}")
    payload = admin_client.get("/api/update-status").json()
    assert payload["update_available"] is False


def test_not_reachable_is_not_up_to_date(admin_client, monkeypatch):
    github_is_down(monkeypatch)
    payload = admin_client.get("/api/update-status").json()
    assert payload["enabled"] is True
    assert payload["reachable"] is False
    assert "update_available" not in payload


def test_the_switch_keeps_github_out_of_it(admin_client, db, monkeypatch):
    """Off means off: the endpoint answers without any outbound call. The
    switch is read per request, so flipping it needs no restart."""
    from app.schemas.settings import InstanceSettings
    from app.services import settings_store

    current = settings_store.instance_settings(db)
    settings_store.save_instance_settings(
        db, InstanceSettings(**{**current.model_dump(), "update_check_enabled": False}))

    calls: list = []
    github_answers(monkeypatch, "v999.0.0", calls)
    payload = admin_client.get("/api/update-status").json()
    assert payload == {"enabled": False, "current": get_version()}
    assert calls == []


def test_only_the_administrator_may_ask(db, monkeypatch):
    """A user must not be able to make the installation call GitHub."""
    calls: list = []
    github_answers(monkeypatch, "v999.0.0", calls)
    with client_as(db, 2) as user_client:
        assert user_client.get("/api/update-status").status_code == 403
    app.dependency_overrides.clear()
    assert calls == []
