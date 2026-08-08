#!/usr/bin/env python3
"""Set the version in every file that carries it, in one go.

    python scripts/bump_version.py 1.37.0

There are five places and it is genuinely easy to miss one — the lock file holds
the version twice and nobody edits a lock file by hand. Forgetting it used to be
invisible until the release workflow quietly repaired it on ``main``, which then
broke the next branch. Now ``check_versions.py`` fails the pull request instead,
and this script is how you keep it green.

It only touches the version. The changelog entry is yours to write, because a
release note is the one part of a release that cannot be derived.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: bump_version.py <version>, for example 1.37.0")
    version = sys.argv[1].lstrip("v").strip()
    if not SEMVER.match(version):
        raise SystemExit(f"{version!r} is not a semantic version like 1.37.0")

    for name in ("VERSION", "backend/VERSION"):
        (ROOT / name).write_text(version + "\n", encoding="utf-8")

    for name in ("frontend/package.json", "frontend/package-lock.json"):
        path = ROOT / name
        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = version
        # The lock file repeats the version for the root package. npm keeps the
        # two in step and so must we, or half of it stays behind.
        if "packages" in data and "" in data["packages"]:
            data["packages"][""]["version"] = version
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    print(f"Version set to {version} in 5 places.")
    if f"## [{version}]" not in changelog:
        print(f"CHANGELOG.md has no section for {version} yet — that part is yours.")


if __name__ == "__main__":
    main()
