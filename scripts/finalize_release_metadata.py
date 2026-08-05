"""Normaliseer afgeleide releasebestanden voordat een release-tag wordt gezet."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

    package_path = ROOT / "frontend" / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("version") != version:
        raise SystemExit(
            f"frontend/package.json is {package.get('version')!r}, expected {version!r}"
        )

    lock_path = ROOT / "frontend" / "package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["version"] = version
    lock.setdefault("packages", {}).setdefault("", {})["version"] = version
    lock_path.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    changelog_path = ROOT / "CHANGELOG.md"
    archive_path = ROOT / "CHANGELOG-1.29.5-and-earlier.md"
    changelog = changelog_path.read_text(encoding="utf-8")

    if archive_path.exists():
        archive = archive_path.read_text(encoding="utf-8")
        first_release = archive.find("## [")
        if first_release < 0:
            raise SystemExit("The archived changelog contains no release heading")

        previous_releases = changelog.find("\n## Previous releases")
        if previous_releases >= 0:
            changelog = changelog[:previous_releases]

        changelog_path.write_text(
            changelog.rstrip() + "\n\n" + archive[first_release:].lstrip(),
            encoding="utf-8",
        )
        archive_path.unlink()

    final_changelog = changelog_path.read_text(encoding="utf-8")
    if f"## [{version}]" not in final_changelog:
        raise SystemExit(f"CHANGELOG.md contains no section for {version}")


if __name__ == "__main__":
    main()
