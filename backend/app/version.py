from pathlib import Path

_VERSION_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "VERSION",
    Path(__file__).resolve().parents[2] / "VERSION",
]


def get_version() -> str:
    for path in _VERSION_CANDIDATES:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return "0.0.0-dev"
