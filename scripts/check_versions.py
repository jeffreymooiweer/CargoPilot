#!/usr/bin/env python3
"""Fail CI when CargoPilot's published version files disagree."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_version(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def main() -> None:
    versions = {
        "VERSION": read_version(ROOT / "VERSION"),
        "backend/VERSION": read_version(ROOT / "backend" / "VERSION"),
        "frontend/package.json": json.loads(
            (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
        )["version"],
    }
    unique = set(versions.values())
    if len(unique) != 1:
        details = ", ".join(f"{name}={version}" for name, version in versions.items())
        raise SystemExit(f"CargoPilot version mismatch: {details}")
    version = unique.pop()
    print(f"CargoPilot version is consistent: {version}")


if __name__ == "__main__":
    main()
