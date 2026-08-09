"""A release does not change main.

Five places carry the version number, and the lockfile carries it twice. That
lockfile was not checked, so it lagged behind on every release, and the release
workflow repaired that with a commit to ``main`` *after* the merge.

That repair worked, and caused the problem: main slid out from under the next
branch, which then conflicted on ``VERSION`` and ``CHANGELOG.md`` and could only
be merged after a rebase. Twice in one day, and the cause was four lines of JSON.

The check now sits in the CI of every pull request, where the mistake is made.
These tests record that it really does see all five places — a check that skips
the lockfile is precisely the check that let this happen.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "check_versions.py"
BUMP = ROOT / "scripts" / "bump_version.py"

VERSION_FILES = (
    "VERSION",
    "backend/VERSION",
    "frontend/package.json",
    "frontend/package-lock.json",
)


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], capture_output=True, text=True, cwd=ROOT
    )


@pytest.fixture
def restore():
    """Restore the version files after a test that deliberately breaks them."""
    saved = {name: (ROOT / name).read_text(encoding="utf-8") for name in VERSION_FILES}
    yield
    for name, text in saved.items():
        (ROOT / name).write_text(text, encoding="utf-8")


def test_the_repository_is_consistent_right_now():
    result = run(CHECK)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("name", VERSION_FILES)
def test_every_version_file_is_actually_checked(name, restore):
    """Put one of them on a different number and the check should fail."""
    path = ROOT / name
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = "0.0.1"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text("0.0.1\n", encoding="utf-8")

    result = run(CHECK)
    assert result.returncode == 1
    assert name in result.stderr


def test_the_second_version_inside_the_lock_file_is_checked_too(restore):
    """npm writes it twice. Whoever checks one of them misses half a mistake —
    and that is exactly what happened."""
    path = ROOT / "frontend" / "package-lock.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["packages"][""]["version"] = "0.0.1"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    result = run(CHECK)
    assert result.returncode == 1
    assert 'packages[""]' in result.stderr


def test_bumping_sets_all_five_at_once(restore):
    assert run(BUMP, "9.9.9").returncode == 0
    assert run(CHECK).returncode == 0

    lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["version"] == "9.9.9"
    assert lock["packages"][""]["version"] == "9.9.9"
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "9.9.9"


def test_bumping_leaves_the_lock_file_otherwise_untouched(restore):
    """Rewriting a lockfile must not add noise to the diff; otherwise a version
    bump becomes unreadable and nobody looks at it any more."""
    path = ROOT / "frontend" / "package-lock.json"
    before = json.loads(path.read_text(encoding="utf-8"))
    run(BUMP, "9.9.9")
    after = json.loads(path.read_text(encoding="utf-8"))

    before["version"] = after["version"] = ""
    before["packages"][""]["version"] = after["packages"][""]["version"] = ""
    assert before == after


@pytest.mark.parametrize("bad", ["banana", "1.2", "v1.2.3.4", ""])
def test_a_version_that_is_not_a_version_is_refused(bad, restore):
    assert run(BUMP, bad).returncode != 0


def test_a_v_prefix_is_accepted_because_tags_carry_one(restore):
    assert run(BUMP, "v9.9.9").returncode == 0
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "9.9.9"


def test_the_release_workflow_no_longer_writes_to_main():
    """The heart of the matter. Tagging must not move main."""
    workflow = (ROOT / ".github" / "workflows" / "tag-release.yml").read_text(encoding="utf-8")
    assert "HEAD:main" not in workflow
    assert "finalize_release_metadata" not in workflow
    # What it does instead: check, and stop when it does not add up.
    assert "scripts/check_versions.py" in workflow


def test_the_pull_request_gate_exists():
    """If this disappears from CI, the problem comes back through the back door."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/check_versions.py" in ci
