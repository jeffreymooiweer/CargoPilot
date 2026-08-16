"""The local model runtime: llama.cpp's server, managed as a child process.

Nothing of this ships in the image. When an admin enables the assistant, the
server binary for this machine's architecture and the GGUF model are
downloaded once into ``/data/assistant`` — each verified against the SHA-256
pinned in ``assistant_runtime.json``, the way the document store pins its
sources. A pin of ``null`` means nobody has hashed that artifact yet, and the
download refuses to run rather than trust the network.

The model's only job is translation (see the orchestrator): every call is
constrained to a JSON schema by llama.cpp's grammar support, so output that
is not the expected structure cannot exist. When the runtime is absent,
downloading, or broken, the assistant keeps working on its deterministic
floor — this module failing may never take the chat down.
"""
from __future__ import annotations

import hashlib
import json
import logging
import platform
import shutil
import socket
import subprocess
import tarfile
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "assistant_runtime.json"
)

_lock = threading.Lock()
_process: subprocess.Popen | None = None
_port: int | None = None
_download: dict[str, Any] = {"state": "idle", "detail": ""}


def sources() -> dict[str, Any]:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - config missing
        return {}


def _arch() -> str:
    machine = platform.machine().lower()
    return "aarch64" if machine in ("aarch64", "arm64") else "x86_64"


def assistant_dir() -> Path:
    return Path(get_settings().data_dir) / "assistant"


def _server_binary() -> Path:
    return assistant_dir() / "bin" / "llama-server"


def _model_path() -> Path:
    filename = (sources().get("model") or {}).get("filename") or "model.gguf"
    return assistant_dir() / filename


def installed() -> bool:
    return _server_binary().exists() and _model_path().exists()


def status() -> dict[str, Any]:
    config = sources()
    server_pin = (config.get("server") or {}).get(_arch()) or {}
    return {
        "available": True,
        "mode": "model" if installed() else "deterministic",
        "model": (config.get("model") or {}).get("name") if installed() else None,
        "installed": installed(),
        "installable": bool(server_pin.get("sha256")
                            and (config.get("model") or {}).get("sha256")),
        "architecture": _arch(),
        "download": dict(_download),
        "running": _process is not None and _process.poll() is None,
    }


# --- download --------------------------------------------------------------

def _fetch_verified(url: str, sha256: str, destination: Path, label: str) -> None:
    """Stream a pinned artifact to disk and refuse it unless the digest
    matches. A wrong hash removes the file: half-trusted bytes are worse
    than absent bytes."""
    _download.update({"state": "downloading", "detail": label})
    digest = hashlib.sha256()
    temp = destination.with_suffix(destination.suffix + ".part")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=60.0) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with temp.open("wb") as handle:
                for chunk in response.iter_bytes(1024 * 512):
                    handle.write(chunk)
                    digest.update(chunk)
    found = digest.hexdigest()
    if found != sha256:
        temp.unlink(missing_ok=True)
        raise ValueError(
            f"{label}: sha256 mismatch (expected {sha256[:16]}…, got {found[:16]}…)")
    temp.replace(destination)


def _install(config: dict[str, Any]) -> None:
    server_pin = (config.get("server") or {}).get(_arch()) or {}
    model_pin = config.get("model") or {}
    base = assistant_dir()

    archive = base / "server.tar.gz"
    _fetch_verified(server_pin["url"], server_pin["sha256"], archive, "server")
    _download.update({"state": "downloading", "detail": "unpack"})
    bin_dir = base / "bin"
    if bin_dir.exists():
        shutil.rmtree(bin_dir)
    bin_dir.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            name = Path(member.name).name
            if not member.isfile() or not (
                    name == "llama-server" or name.endswith(".so") or ".so." in name):
                continue
            source = bundle.extractfile(member)
            if source is None:  # pragma: no cover - directory entries
                continue
            with source, (bin_dir / name).open("wb") as target:
                shutil.copyfileobj(source, target)
    archive.unlink(missing_ok=True)
    server = bin_dir / "llama-server"
    if not server.exists():
        raise ValueError("server: archive held no llama-server binary")
    server.chmod(0o755)

    _fetch_verified(model_pin["url"], model_pin["sha256"], _model_path(), "model")
    _download.update({"state": "done", "detail": ""})


def start_download() -> dict[str, Any]:
    """Fetch binary and model in a background thread; progress in status()."""
    config = sources()
    server_pin = (config.get("server") or {}).get(_arch()) or {}
    model_pin = config.get("model") or {}
    if not server_pin.get("sha256") or not model_pin.get("sha256"):
        return {"error": "sources_not_pinned"}
    if _download.get("state") == "downloading":
        return {"error": "already_downloading"}

    def run() -> None:
        try:
            _install(config)
        except Exception as exc:  # noqa: BLE001 - reported in status, never raised
            logger.warning("Assistant install failed: %s", exc)
            _download.update({"state": "error", "detail": str(exc)})

    _download.update({"state": "downloading", "detail": "start"})
    threading.Thread(target=run, daemon=True).start()
    return {"started": True}


def remove() -> dict[str, Any]:
    stop()
    if assistant_dir().exists():
        shutil.rmtree(assistant_dir())
    _download.update({"state": "idle", "detail": ""})
    return {"removed": True}


# --- the server process ----------------------------------------------------

def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _base_url() -> str:
    return f"http://127.0.0.1:{_port}"


def ensure_server(timeout: float = 60.0) -> bool:
    """Start llama-server once and wait for its health endpoint."""
    global _process, _port
    if not installed():
        return False
    with _lock:
        if _process is not None and _process.poll() is None:
            return True
        _port = _free_port()
        binary = _server_binary()
        _process = subprocess.Popen(
            [str(binary), "-m", str(_model_path()), "--host", "127.0.0.1",
             "--port", str(_port), "-c", "4096", "--no-webui"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={"LD_LIBRARY_PATH": str(binary.parent)},
        )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _process.poll() is not None:
            return False
        try:
            response = httpx.get(f"{_base_url()}/health", timeout=2.0)
            if response.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    return False


def stop() -> None:
    global _process
    with _lock:
        if _process is not None and _process.poll() is None:
            _process.terminate()
            try:
                _process.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - stubborn child
                _process.kill()
        _process = None


# --- constrained extraction ------------------------------------------------

def extract_json(
    system: str, user: str, schema: dict[str, Any], timeout: float = 120.0,
) -> dict[str, Any] | None:
    """One schema-constrained completion; None on any failure.

    The grammar makes output outside the schema impossible; a runtime
    failure makes the caller fall back to the deterministic route. Either
    way the orchestrator's rules hold.
    """
    if not ensure_server():
        return None
    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "extraction", "schema": schema},
        },
    }
    try:
        response = httpx.post(
            f"{_base_url()}/v1/chat/completions", json=payload, timeout=timeout)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.warning("Assistant extraction failed: %s", exc)
        return None
