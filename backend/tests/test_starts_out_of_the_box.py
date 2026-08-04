"""De app moet starten met de instellingen waarmee zij wordt uitgeleverd.

Dit is de test die ontbrak. Van v1.25.0 tot v1.29.2 weigerde CargoPilot te
starten zodra `APP_SECRET_KEY` op de standaardwaarde stond of leeg was, en
zodra `CORS_ALLOWED_ORIGINS` op `*` stond — en dat zíjn de standaardwaarden van
deze applicatie, plus wat de Unraid-sjabloon meegeeft. Elke installatie die die
twee niet uit zichzelf had ingevuld, viel om bij het opstarten.

De 500 tests die er toen al waren, vonden het niet. Allemaal draaiden ze met
`APP_ENV=test`, waarmee de controle juist wordt overgeslagen, en geen enkele
bouwde de applicatie zoals een gebruiker haar start.

Vandaar deze: een echt los proces, met een schone omgeving, zonder `.env`, en
zonder één instelling die een gebruiker niet ook zou hebben. Zij draait
opzettelijk niet in het testproces, want juist de omgeving is hier het
onderwerp.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]

BUILD_THE_APP = """
from app.main import create_app
from app.core.config import get_settings

create_app()
print("STARTED", get_settings().app_secret_key[:8])
"""


def start_with(env_dir: Path, **overrides) -> subprocess.CompletedProcess:
    """Bouw de applicatie in een los proces, met een omgeving die we kennen."""
    env_dir.mkdir(parents=True, exist_ok=True)
    env = {
        # Een schone omgeving: alleen wat een container ook heeft. PATH en HOME
        # blijven van het systeem — HOME wijst hier naar de user-site waar een
        # deel van de pakketten staat, en die weghalen zou Python zelf slopen in
        # plaats van de configuratie te beproeven.
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": str(BACKEND),
        "DATA_DIR": str(env_dir),
        "DATABASE_URL": f"sqlite:///{env_dir}/cargopilot.db",
        # Zonder dit probeert het opstarten catalogi van internet te halen.
        "CATALOG_AUTO_SYNC": "false",
    }
    env.update({k: v for k, v in overrides.items() if v is not None})
    return subprocess.run(
        [sys.executable, "-c", BUILD_THE_APP],
        cwd=env_dir,  # niet in de repo, dus geen .env die meekomt
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_the_app_starts_with_nothing_configured(tmp_path):
    """Geen APP_ENV, geen APP_SECRET_KEY, geen CORS — zoals iemand die de
    container aanzet en verder niets invult."""
    result = start_with(tmp_path)
    assert "STARTED" in result.stdout, result.stderr[-3000:]


def test_the_app_starts_the_way_the_unraid_template_configures_it(tmp_path):
    """De sjabloon in unraid/CargoPilot.xml geeft APP_SECRET_KEY leeg mee."""
    result = start_with(tmp_path, APP_SECRET_KEY="")
    assert "STARTED" in result.stdout, result.stderr[-3000:]


def test_the_app_starts_on_the_published_default_secret(tmp_path):
    result = start_with(tmp_path, APP_SECRET_KEY="change-me")
    assert "STARTED" in result.stdout, result.stderr[-3000:]


def test_it_does_not_sign_with_the_published_key_it_was_given(tmp_path):
    """Starten is niet genoeg — het moest ook veilig."""
    result = start_with(tmp_path, APP_SECRET_KEY="change-me")
    assert "STARTED" in result.stdout, result.stderr[-3000:]
    assert "STARTED change-me" not in result.stdout
    assert (tmp_path / "secret_key").exists()


def test_a_restart_keeps_everyone_logged_in(tmp_path):
    """Een nieuwe sleutel bij elke herstart zou iedereen eruit gooien."""
    first = start_with(tmp_path)
    second = start_with(tmp_path)
    assert "STARTED" in first.stdout and "STARTED" in second.stdout
    assert first.stdout.strip() == second.stdout.strip()


def test_a_key_of_your_own_is_the_one_that_is_used(tmp_path):
    own = "x" * 40
    result = start_with(tmp_path, APP_SECRET_KEY=own)
    assert f"STARTED {own[:8]}" in result.stdout, result.stderr[-3000:]


@pytest.mark.parametrize("app_env", ["production", "staging", "development"])
def test_it_starts_in_every_environment(app_env, tmp_path):
    result = start_with(tmp_path / app_env, APP_ENV=app_env)
    assert "STARTED" in result.stdout, result.stderr[-3000:]
