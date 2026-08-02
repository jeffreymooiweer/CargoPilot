"""The version number lives in several files; they have to agree.

`backend/VERSION` takes priority over the repository root `VERSION` in
`app.version.get_version()`, so a stale copy makes `/api/health` report an old
release without anything else going wrong. That happened once; this test keeps
it from happening again.
"""

import json
from pathlib import Path

from app.version import get_version

REPO = Path(__file__).resolve().parents[2]


def test_all_version_files_agree():
    root = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    backend = (REPO / "backend" / "VERSION").read_text(encoding="utf-8").strip()
    package = json.loads((REPO / "frontend" / "package.json").read_text(encoding="utf-8"))

    assert backend == root, "backend/VERSION is out of step with the root VERSION"
    assert package["version"] == root, "frontend/package.json is out of step with VERSION"
    assert get_version() == root


def test_the_changelog_documents_the_current_version():
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{get_version()}]" in changelog
