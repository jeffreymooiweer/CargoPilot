"""Elke stap één keer, en emulatie alleen als er iets wordt gepubliceerd.

Er stonden twee workflows in deze repository die allebei ``CI`` heetten en
allebei op dezelfde duw afgingen: ``ci.yml`` en ``dockerhub.yml``. Ze deden
grotendeels hetzelfde. ``pytest`` liep twee keer, ``npm ci`` liep twee keer, en
er stonden vijf checks onder een pull request waarvan er twee een kopie waren
van twee andere. Bij een release met drie commits op de branch waren dat vijftien
jobs voordat er iets gemerged was.

De tweede kostenpost was de Docker-build. Die vroeg altijd om ``linux/arm64``,
ook op een pull request, waar het resultaat daarna werd weggegooid omdat er niets
wordt gepusht. arm64 draait op een amd64-runner onder QEMU, en die emulatie was
het leeuwendeel van de looptijd.

Dat soort dubbel werk sluipt er ongemerkt weer in — een tweede workflow is zo
toegevoegd en niemand telt de checks. Vandaar deze tests. Ze lezen de YAML als
tekst; dat is bewust grof, want wat hier wordt bewaakt is niet de precieze
formulering maar de vorm: één workflow die vanzelf draait, geen duplicaten,
en geen emulatie zonder publicatie.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def load(name: str) -> dict:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    # PyYAML leest de sleutel `on:` als de booleaanse waarde True.
    return yaml.safe_load(text)


def triggers(definition: dict) -> dict:
    return definition.get("on") or definition.get(True) or {}


def steps_only(name: str) -> str:
    """De workflow zonder commentaar.

    Deze bestanden leggen in commentaar uit wat er misging, en daarin staan de
    woorden die deze tests tellen — "dockerhub.yml", "npm ci". Zonder deze
    zeef meet een test zijn eigen toelichting.
    """
    lines = (WORKFLOWS / name).read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def automatic() -> list[str]:
    """De workflows die uit zichzelf beginnen, en dus geld kosten per duw."""
    started = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        on = triggers(load(path.name))
        if {"push", "pull_request", "schedule"} & set(on):
            started.append(path.name)
    return started


# --- Wat er vanzelf draait ------------------------------------------------


def test_only_two_workflows_start_by_themselves():
    """ci.yml op elke duw, en tag-release.yml op een gemergede releasebranch.
    Alle andere wachten tot iemand erom vraagt en kosten tot dat moment niets."""
    assert automatic() == ["ci.yml", "tag-release.yml"]


def test_no_two_workflows_share_a_name():
    """Twee keer "CI" in de lijst is precies hoe het dubbele werk zo lang
    onzichtbaar bleef."""
    names = [load(p.name).get("name") for p in sorted(WORKFLOWS.glob("*.yml"))]
    assert len(names) == len(set(names)), names


def test_the_duplicate_is_gone():
    assert not (WORKFLOWS / "dockerhub.yml").exists()
    assert not (WORKFLOWS / "release.yml").exists()


def test_nothing_still_points_at_the_deleted_workflow():
    """De tag-workflow zwengelt de build op de tag-ref aan; wijst die naar een
    bestand dat niet meer bestaat, dan komt er stilzwijgend geen image."""
    for path in WORKFLOWS.glob("*.yml"):
        assert "dockerhub.yml" not in steps_only(path.name), path.name


# --- Eén keer per duw -----------------------------------------------------


def test_the_test_suites_run_exactly_once_per_push():
    everything = "\n".join(steps_only(name) for name in automatic())
    assert everything.count("pytest -q") == 1
    assert everything.count("npm ci") == 1


@pytest.mark.parametrize("step", ["npm test", "npm run build", "npm audit"])
def test_the_frontend_checks_survived_the_merge(step):
    """Bij het samenvoegen is de uitgebreidste van de twee frontend-jobs
    aangehouden. De audit en de tests zaten alleen in ci.yml en mogen niet
    sneuvelen omdat de andere job korter was."""
    assert step in (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")


# --- Geen emulatie zonder publicatie --------------------------------------


def test_arm64_is_not_hardcoded_into_the_build():
    """Stond het er vast, dan bouwde elke pull request het weer — onder QEMU,
    en voor niets."""
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "platforms: linux/amd64,linux/arm64" not in ci
    assert "platforms: ${{ steps.plan.outputs.platforms }}" in ci


def test_a_pull_request_builds_one_architecture_and_publishes_nothing():
    plan = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    start = plan.index("Decide what to build")
    branch = plan[start: plan.index("Check DockerHub credentials")]
    pull_request_half = branch[: branch.index("else")]
    assert "linux/amd64" in pull_request_half
    assert "linux/arm64" not in pull_request_half
    assert "publishing=false" in pull_request_half


def test_qemu_is_only_set_up_when_arm64_is_wanted():
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    qemu = ci[ci.index("Set up QEMU"):]
    assert "if: steps.plan.outputs.publishing == 'true'" in qemu[: qemu.index("uses:")]


# --- Niet twee keer dezelfde uitslag --------------------------------------


def test_a_superseded_pull_request_run_is_cancelled():
    ci = load("ci.yml")
    assert ci["concurrency"]["cancel-in-progress"] == (
        "${{ github.event_name == 'pull_request' }}"
    )


def test_but_a_publishing_run_is_never_cancelled():
    """main en een tag draaien af: daar hangt een image aan. De expressie
    hierboven regelt dat al, maar het is het soort ding dat iemand ooit
    vereenvoudigt tot `true`."""
    ci = load("ci.yml")
    assert ci["concurrency"]["cancel-in-progress"] != True  # noqa: E712


# --- Een tag is een naam, geen bouwopdracht -------------------------------
#
# De release bouwde dezelfde commit een tweede keer, nu op de tag-ref: vier tot
# zes minuten om precies dezelfde bits te vertalen, met de testsuites er nog
# eens overheen. Main had die image al gebouwd, getest en gepusht onder zijn
# korte SHA. `imagetools create` zet de versienaam server-side op dat manifest.


def test_the_release_does_not_rebuild_what_main_already_built():
    tag_release = steps_only("tag-release.yml")
    assert "imagetools create" in tag_release
    assert "gh workflow run" not in tag_release


def test_the_released_image_is_the_one_that_was_tested():
    """Het manifest wordt hernoemd, niet nagemaakt. Een tweede vertaling van
    dezelfde broncode kan er net naast zitten; hetzelfde manifest niet."""
    tag_release = steps_only("tag-release.yml")
    assert "rev-parse --short=7 HEAD" in tag_release
    assert 'imagetools create -t "$IMAGE:$VERSION" "$IMAGE:$SHORT"' in tag_release


def test_it_gives_up_rather_than_release_an_older_image():
    """Als de build op main faalde is er geen geteste image. Dan is stoppen
    beter dan een versietag op iets van gisteren."""
    tag_release = steps_only("tag-release.yml")
    assert "never appeared" in tag_release
    assert "exit 1" in tag_release


def test_ci_no_longer_runs_on_a_tag():
    """Anders bestaan er weer twee manieren waarop een versie-image ontstaat,
    en die lopen op den duur uiteen."""
    assert "tags" not in triggers(load("ci.yml"))["push"]


# --- Het leesgereedschap draait niet meer mee ------------------------------


def test_reading_a_regulation_is_something_you_ask_for():
    """Deze workflow haalde vier PDF's van samen zo'n 40 MB op bij elke duw die
    het script raakte, op een branch waar niemand de log las."""
    on = triggers(load("read-land-regulations.yml"))
    assert set(on) == {"workflow_dispatch"}
