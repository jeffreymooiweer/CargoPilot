"""In-app updating: capable only where the operator said so, honest always.

The swap itself needs a real Docker daemon and is exercised in life; what
these tests hold is everything around it — the capability answer for every
way of not being able, the refusal paths of the API, the exact requests
the update sends to the daemon, and the helper's successor payload and
rollback, all against a scripted Docker API.
"""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import get_settings
from app.services import updater
from app import update_helper


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler),
                        base_url="http://docker")


def test_capability_reports_the_switch_first(data_dir, monkeypatch):
    monkeypatch.delenv("UPDATE_APPLY_ENABLED", raising=False)
    get_settings.cache_clear()
    ability = updater.capability()
    assert ability["available"] is False
    assert ability["reason"] == "switch_off"


def test_capability_reports_a_missing_socket(data_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("UPDATE_APPLY_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(updater, "DOCKER_SOCKET", tmp_path / "no-socket")
    ability = updater.capability()
    assert ability["available"] is False
    assert ability["reason"] == "no_socket"


def _socket(tmp_path, monkeypatch):
    socket = tmp_path / "docker.sock"
    socket.write_bytes(b"")
    monkeypatch.setattr(updater, "DOCKER_SOCKET", socket)


def test_capability_refuses_a_foreign_image(data_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("UPDATE_APPLY_ENABLED", "true")
    get_settings.cache_clear()
    _socket(tmp_path, monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "Id": "a" * 64, "Config": {"Image": "somebody/else:latest"}})

    monkeypatch.setattr(updater, "docker_client", lambda: make_client(handler))
    monkeypatch.setattr(updater, "own_container_id", lambda client: "a" * 64)
    ability = updater.capability()
    assert ability["available"] is False
    assert ability["reason"] == "foreign_image"


def test_own_container_id_verifies_against_the_daemon(monkeypatch):
    known = "b" * 64

    def handler(request: httpx.Request) -> httpx.Response:
        if known in request.url.path:
            return httpx.Response(200, json={"Id": known})
        return httpx.Response(404)

    monkeypatch.setenv("HOSTNAME", "not-a-container-id")
    monkeypatch.setattr(
        updater, "Path",
        lambda p: SimpleNamespace(read_text=lambda **k: f"0::/docker/{known}\n"))
    with make_client(handler) as client:
        assert updater.own_container_id(client) == known


def test_start_update_pulls_and_hands_over(data_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("UPDATE_APPLY_ENABLED", "true")
    get_settings.cache_clear()
    _socket(tmp_path, monkeypatch)
    own_id = "c" * 64
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if path == "/images/create":
            return httpx.Response(200, text=json.dumps({"status": "ok"}) + "\n")
        if path.startswith("/images/") and path.endswith("/json"):
            return httpx.Response(200, json={"Id": "sha256:new"})
        if path == f"/containers/{own_id}/json":
            return httpx.Response(200, json={
                "Id": own_id,
                "Config": {"Image": updater.IMAGE_REPOSITORY + ":v1.132.0"},
                "HostConfig": {"Binds": ["/srv/data:/data"]},
            })
        if path == "/containers/create":
            body = json.loads(request.read())
            assert body["Image"] == updater.IMAGE_REPOSITORY + ":v1.133.0"
            assert body["Entrypoint"] == ["python", "-m", "app.update_helper"]
            assert body["Cmd"] == [own_id, body["Image"]]
            assert "/srv/data:/data" in body["HostConfig"]["Binds"]
            assert any(b.endswith("docker.sock") or "docker.sock" in b
                       for b in body["HostConfig"]["Binds"])
            return httpx.Response(201, json={"Id": "helper123"})
        if path == "/containers/helper123/start":
            return httpx.Response(204)
        return httpx.Response(404)

    monkeypatch.setattr(updater, "docker_client", lambda: make_client(handler))
    monkeypatch.setattr(updater, "own_container_id", lambda client: own_id)
    result = updater.start_update("1.133.0")
    assert result["to"] == "1.133.0"
    assert "POST /images/create" in calls
    assert "POST /containers/create" in calls
    state = json.loads((tmp_path / "update-state.json").read_text())
    assert state["phase"] == "handed_over"


def test_start_update_refuses_a_non_version(data_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("UPDATE_APPLY_ENABLED", "true")
    get_settings.cache_clear()
    _socket(tmp_path, monkeypatch)
    monkeypatch.setattr(updater, "capability", lambda: {
        "available": True, "container": "c" * 64,
        "image": updater.IMAGE_REPOSITORY + ":v1"})
    with pytest.raises(updater.UpdateError):
        updater.start_update("latest")
    with pytest.raises(updater.UpdateError):
        updater.start_update("1.2.3; rm -rf /")


def test_the_successor_keeps_the_configuration():
    old = {
        "Id": "d" * 64,
        "Config": {"Env": ["A=1"], "Labels": {"x": "y"},
                   "ExposedPorts": {"8000/tcp": {}}},
        "HostConfig": {"Binds": ["/srv:/data"], "RestartPolicy":
                       {"Name": "unless-stopped"}, "LogConfig": {"Type": "json-file"},
                       "OomScoreAdj": 123},
        "NetworkSettings": {"Networks": {"bridge": {"Aliases": None}}},
    }
    payload = update_helper.successor_payload(old, "repo:v2")
    assert payload["Image"] == "repo:v2"
    assert payload["Env"] == ["A=1"]
    assert payload["HostConfig"]["Binds"] == ["/srv:/data"]
    assert payload["HostConfig"]["RestartPolicy"]["Name"] == "unless-stopped"
    assert "OomScoreAdj" not in payload["HostConfig"]


def test_the_helper_rolls_back_when_the_successor_will_not_start(tmp_path, monkeypatch):
    monkeypatch.setattr(update_helper, "DATA_DIR", tmp_path)
    old_id = "e" * 64
    log: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        log.append(f"{method} {path} {dict(request.url.params)}")
        if path == f"/containers/{old_id}/json":
            return httpx.Response(200, json={
                "Id": old_id, "Name": "/cargopilot",
                "Config": {"Env": ["A=1"]},
                "HostConfig": {"Binds": ["/srv:/data"]},
                "NetworkSettings": {"Networks": {}},
                "State": {"Running": False},
            })
        if path == f"/containers/{old_id}/stop":
            return httpx.Response(204)
        if path == f"/containers/{old_id}/rename":
            return httpx.Response(204)
        if path == "/containers/create":
            return httpx.Response(201, json={"Id": "newbie"})
        if path == "/containers/newbie/start":
            return httpx.Response(500, text="no")
        if path == "/containers/newbie" and method == "DELETE":
            return httpx.Response(204)
        if path == f"/containers/{old_id}/start":
            return httpx.Response(204)
        return httpx.Response(404)

    real_client = httpx.Client
    monkeypatch.setattr(
        update_helper.httpx, "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler),
                                     base_url="http://docker"))
    monkeypatch.setattr(update_helper, "sys",
                        SimpleNamespace(argv=["x", old_id, "repo:v2"]))
    assert update_helper.main() == 1
    state = json.loads((tmp_path / "update-state.json").read_text())
    assert state["phase"] == "failed"
    # The rollback renamed the old container back and started it again.
    assert any("rename" in line and "cargopilot" in line for line in log)
    assert f"POST /containers/{old_id}/start {{}}" in log


def test_the_api_refuses_without_capability(data_dir, monkeypatch):
    from types import SimpleNamespace as NS
    from fastapi.testclient import TestClient
    from app.core.deps import get_current_user
    from app.main import app

    monkeypatch.delenv("UPDATE_APPLY_ENABLED", raising=False)
    get_settings.cache_clear()
    app.dependency_overrides[get_current_user] = lambda: NS(
        id=1, username="admin", role="admin", active=True)
    try:
        with TestClient(app) as client:
            ability = client.get("/api/update-capability")
            assert ability.status_code == 200
            assert ability.json()["available"] is False
            response = client.post("/api/update-apply")
            assert response.status_code == 409
            assert response.json()["detail"]["reason"] == "switch_off"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
