"""Een release verandert main niet.

Vijf plekken dragen het versienummer, en de lockfile draagt hem twee keer. Die
lockfile werd niet gecontroleerd, dus hij liep bij elke release achter, en de
release-workflow repareerde dat met een commit naar ``main`` *na* de merge.

Die reparatie werkte, en veroorzaakte het probleem: main schoof onder de
volgende branch vandaan, die daarna conflicteerde op ``VERSION`` en
``CHANGELOG.md`` en pas na een rebase te mergen was. Twee keer op één dag, en de
oorzaak waren vier regels JSON.

De controle staat nu in de CI van elke pull request, waar de vergissing wordt
gemaakt. Deze tests leggen vast dat hij ook echt alle vijf de plekken ziet — een
controle die de lockfile overslaat is precies de controle die dit liet gebeuren.
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
    """Herstel de versiebestanden na een test die ze opzettelijk sloopt."""
    saved = {name: (ROOT / name).read_text(encoding="utf-8") for name in VERSION_FILES}
    yield
    for name, text in saved.items():
        (ROOT / name).write_text(text, encoding="utf-8")


def test_the_repository_is_consistent_right_now():
    result = run(CHECK)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("name", VERSION_FILES)
def test_every_version_file_is_actually_checked(name, restore):
    """Zet er één op een ander nummer en de controle hoort te vallen."""
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
    """npm schrijft hem twee keer. Wie er één controleert, mist een halve fout —
    en dat is precies wat er gebeurde."""
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
    """Een lockfile herschrijven mag geen ruis in de diff geven; anders wordt
    een versiebump onleesbaar en gaat niemand er nog naar kijken."""
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
    """De kern van de zaak. Taggen mag main niet verplaatsen."""
    workflow = (ROOT / ".github" / "workflows" / "tag-release.yml").read_text(encoding="utf-8")
    assert "HEAD:main" not in workflow
    assert "finalize_release_metadata" not in workflow
    # Wat het in plaats daarvan doet: controleren en stoppen als het niet klopt.
    assert "scripts/check_versions.py" in workflow


def test_the_pull_request_gate_exists():
    """Als dit uit de CI verdwijnt, komt het probleem via de achterdeur terug."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/check_versions.py" in ci
