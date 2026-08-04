"""De app hoort veilig te starten, niet te weigeren te starten.

`APP_SECRET_KEY` tekent de JWT waarmee iemand is ingelogd, en de
standaardwaarde `change-me` staat in deze repository. Een installatie die hem
nooit heeft gezet draait dus op een sleutel die iedereen kan opzoeken, en wie
de sleutel heeft schrijft zelf een geldig beheerderstoken.

Van v1.25.0 tot v1.29.2 loste CargoPilot dat op door te weigeren te starten.
Dat was fout, en het bewijs staat in de standaardwaarden van de applicatie
zelf: `APP_SECRET_KEY=change-me` en `CORS_ALLOWED_ORIGINS=*`, plus een
Unraid-sjabloon dat de sleutel leeg laat. Elke installatie die die twee niet
uit zichzelf had ingevuld crashte bij het opstarten, in een container die zo
snel afsloot dat de melding onleesbaar was. Veiliger werd er niets van — de
app was weg.

Deze tests leggen het gedrag vast dat er wél hoort te zijn: een app met een
eigen gegevensmap maakt zelf een sleutel, bewaart die, en start. En hij blijft
van een sleutel af die de beheerder zelf heeft gezet.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.core.security_checks import (
    MINIMUM_SECRET_LENGTH,
    PUBLISHED_SECRETS,
    SECRET_KEY_FILENAME,
    apply_security_configuration,
    configuration_warnings,
    ensure_secret_key,
    is_production,
    is_usable_secret,
    suggested_secret,
)


@dataclass
class FakeSettings:
    """Genoeg van Settings om de controle te voeden, zonder .env of omgeving."""

    data_dir: Path = Path("/nonexistent")
    app_env: str = "production"
    app_secret_key: str = field(default_factory=suggested_secret)
    cors_allowed_origins: str = "https://cargopilot.example.com"
    admin_password: str | None = None


@pytest.fixture
def settings(tmp_path):
    return FakeSettings(data_dir=tmp_path)


# --- Waar het misging: de app moet starten --------------------------------


def test_the_shipped_defaults_start_instead_of_crashing(tmp_path):
    """Precies de configuratie waarmee CargoPilot uit de doos komt, en waarmee
    elke Unraid-installatie sinds v1.25.0 omviel."""
    out_of_the_box = FakeSettings(
        data_dir=tmp_path, app_secret_key="change-me", cors_allowed_origins="*"
    )
    apply_security_configuration(out_of_the_box)  # geen uitzondering
    assert is_usable_secret(out_of_the_box.app_secret_key)


def test_an_empty_secret_starts_too(tmp_path):
    """De Unraid-sjabloon geeft APP_SECRET_KEY mee met een lege waarde."""
    blank = FakeSettings(data_dir=tmp_path, app_secret_key="")
    apply_security_configuration(blank)
    assert is_usable_secret(blank.app_secret_key)


def test_the_generated_key_is_stored_next_to_the_database(tmp_path):
    settings = FakeSettings(data_dir=tmp_path, app_secret_key="change-me")
    key = ensure_secret_key(settings)
    stored = (tmp_path / SECRET_KEY_FILENAME).read_text(encoding="utf-8").strip()
    assert stored == key


def test_the_same_key_comes_back_after_a_restart(tmp_path):
    """Anders was iedereen na elke herstart van de container uitgelogd."""
    first = ensure_secret_key(FakeSettings(data_dir=tmp_path, app_secret_key="change-me"))
    second = ensure_secret_key(FakeSettings(data_dir=tmp_path, app_secret_key="change-me"))
    assert first == second


def test_the_stored_key_is_not_readable_for_others(tmp_path):
    ensure_secret_key(FakeSettings(data_dir=tmp_path, app_secret_key="change-me"))
    mode = (tmp_path / SECRET_KEY_FILENAME).stat().st_mode
    assert mode & 0o077 == 0, oct(mode)


def test_a_data_directory_that_cannot_be_written_still_starts(tmp_path, caplog):
    """Op Unraid is /data wel eens niet schrijfbaar. Dat mag het opstarten niet
    tegenhouden; het kost alleen dat de sleutel een herstart niet overleeft.

    De map wordt hier onbruikbaar gemaakt door er een bestand op de plek van de
    bovenliggende map te zetten. Rechten afnemen werkt niet: de tests draaien
    vaak als root, en dan is een map zonder schrijfrecht nog steeds schrijfbaar.
    """
    blocked = tmp_path / "afile" / "data"
    (tmp_path / "afile").write_text("geen map", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        key = ensure_secret_key(FakeSettings(data_dir=blocked, app_secret_key=""))

    assert is_usable_secret(key), "de app hoort gewoon te draaien"
    assert "opnieuw inloggen" in caplog.text


# --- En hij blijft van een eigen sleutel af -------------------------------


def test_a_key_the_administrator_set_is_left_alone(tmp_path):
    own = suggested_secret()
    settings = FakeSettings(data_dir=tmp_path, app_secret_key=own)
    apply_security_configuration(settings)
    assert settings.app_secret_key == own
    assert not (tmp_path / SECRET_KEY_FILENAME).exists(), "niets te bewaren"


def test_a_configured_key_wins_over_a_stored_one(tmp_path):
    """Wie zijn sleutel bewust in de omgeving zet, wil dat die geldt — ook als
    er eerder een is gemaakt."""
    ensure_secret_key(FakeSettings(data_dir=tmp_path, app_secret_key=""))
    own = suggested_secret()
    assert ensure_secret_key(FakeSettings(data_dir=tmp_path, app_secret_key=own)) == own


@pytest.mark.parametrize("published", sorted(PUBLISHED_SECRETS))
def test_no_published_value_survives_as_a_key(published, tmp_path):
    """Ook de lange uit .env.example, die langs een pure lengtecontrole glipt."""
    settings = FakeSettings(data_dir=tmp_path, app_secret_key=published)
    apply_security_configuration(settings)
    assert settings.app_secret_key != published


def test_a_key_that_is_too_short_is_replaced(tmp_path):
    settings = FakeSettings(data_dir=tmp_path, app_secret_key="kort")
    apply_security_configuration(settings)
    assert len(settings.app_secret_key) >= MINIMUM_SECRET_LENGTH


def test_a_generated_key_is_long_enough_and_different_every_time():
    first, second = suggested_secret(), suggested_secret()
    assert first != second
    assert len(first) >= MINIMUM_SECRET_LENGTH


@pytest.mark.parametrize("value,usable", [
    (suggested_secret(), True),
    ("change-me", False),
    ("CHANGE-ME", False),
    ("  change-me  ", False),
    ("change-me-to-a-long-random-string", False),
    ("", False),
    (None, False),
    ("x" * (MINIMUM_SECRET_LENGTH - 1), False),
    ("x" * MINIMUM_SECRET_LENGTH, True),
])
def test_what_counts_as_a_usable_key(value, usable):
    assert is_usable_secret(value) is usable


# --- Wat er nog wel gemeld wordt ------------------------------------------


def test_wide_open_cors_is_reported_but_does_not_stop_anything(settings):
    settings.cors_allowed_origins = "*"
    warnings = apply_security_configuration(settings)
    assert any("CORS_ALLOWED_ORIGINS" in w for w in warnings)


def test_a_documented_admin_password_is_reported(settings):
    settings.admin_password = "cargopilot123"
    assert any("ADMIN_PASSWORD" in w for w in configuration_warnings(settings))


def test_a_password_of_your_own_is_not_reported(settings):
    settings.admin_password = "een-eigen-wachtwoord-dat-nergens-staat"
    assert configuration_warnings(settings) == []


def test_the_warnings_reach_the_log(settings, caplog):
    settings.cors_allowed_origins = "*"
    with caplog.at_level(logging.WARNING):
        apply_security_configuration(settings)
    assert "CORS_ALLOWED_ORIGINS" in caplog.text


def test_a_warning_says_what_to_do_about_it(settings):
    settings.cors_allowed_origins = "*"
    assert "CORS_ALLOWED_ORIGINS=https://" in configuration_warnings(settings)[0]


# --- Alleen in productie --------------------------------------------------


@pytest.mark.parametrize("env", ["development", "dev", "local", "test", "testing", "DEV"])
def test_development_is_not_nagged(env, settings):
    settings.app_env = env
    settings.cors_allowed_origins = "*"
    settings.admin_password = "cargopilot123"
    assert configuration_warnings(settings) == []
    assert not is_production(env)


@pytest.mark.parametrize("env", ["production", "prod", "", None, "staging"])
def test_anything_that_is_not_clearly_development_counts_as_production(env):
    assert is_production(env)


def test_development_still_gets_a_usable_key(tmp_path):
    """Ook bij ontwikkelen mag de app niet op een gepubliceerde sleutel tekenen;
    daar is het alleen geen reden om iets te melden."""
    settings = FakeSettings(data_dir=tmp_path, app_env="development", app_secret_key="change-me")
    apply_security_configuration(settings)
    assert is_usable_secret(settings.app_secret_key)
