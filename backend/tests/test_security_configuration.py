"""De app hoort niet te starten met een configuratie die haar open zet.

`APP_SECRET_KEY` tekent de JWT waarmee iemand is ingelogd, en de
standaardwaarde `change-me` staat in deze repository. Een installatie die hem
nooit heeft gezet draait dus op een sleutel die iedereen kan opzoeken, en wie
de sleutel heeft schrijft zelf een geldig beheerderstoken. Dat is geen
schoonheidsfoutje maar een authenticatie die niets tegenhoudt.

Waarschuwen is hier niet genoeg: logs worden niet gelezen en de app blijft
draaien. Deze tests leggen vast dat hij stopt, en dat hij dat alleen in
productie doet — bij ontwikkelen is een vaste bekende sleutel juist praktisch.
"""

from dataclasses import dataclass, field

import pytest

from app.core.security_checks import (
    InsecureConfiguration,
    configuration_problems,
    is_production,
    suggested_secret,
    verify_configuration,
)


@dataclass
class FakeSettings:
    """Genoeg van Settings om de controle te voeden, zonder .env of omgeving."""

    app_env: str = "production"
    app_secret_key: str = field(default_factory=suggested_secret)
    cors_allowed_origins: str = "https://cargopilot.example.com"
    admin_password: str | None = None


def test_a_properly_configured_installation_starts():
    assert configuration_problems(FakeSettings()) == []
    verify_configuration(FakeSettings())  # geen uitzondering


def test_the_published_default_secret_stops_the_app():
    problems = configuration_problems(FakeSettings(app_secret_key="change-me"))
    assert len(problems) == 1
    assert "APP_SECRET_KEY" in problems[0]


@pytest.mark.parametrize("secret", ["change-me", "CHANGE-ME", "dev-secret", "ci-secret", "secret"])
def test_every_secret_that_appears_in_this_repository_is_refused(secret):
    """Een sleutel die in de repo, de docs of de voorbeelden staat is publiek."""
    assert configuration_problems(FakeSettings(app_secret_key=secret))


def test_a_short_secret_is_refused_even_if_it_is_not_a_known_default():
    problems = configuration_problems(FakeSettings(app_secret_key="hunter2"))
    assert any("tekens lang" in p for p in problems)


def test_the_error_says_what_to_do_and_hands_over_a_usable_key():
    """Een foutmelding die de app stillegt moet de oplossing bevatten, anders
    is het alleen maar een blokkade."""
    with pytest.raises(InsecureConfiguration) as error:
        verify_configuration(FakeSettings(app_secret_key="change-me"))
    message = str(error.value)
    assert "APP_SECRET_KEY=" in message
    # De voorgestelde sleutel moet zelf door de controle komen.
    suggested = message.split("APP_SECRET_KEY=")[1].split()[0]
    assert configuration_problems(FakeSettings(app_secret_key=suggested)) == []


def test_wildcard_cors_is_refused_because_the_api_uses_cookies():
    """Met '*' plus cookies mag elke website namens een ingelogde gebruiker
    verzoeken doen."""
    problems = configuration_problems(FakeSettings(cors_allowed_origins="*"))
    assert any("CORS_ALLOWED_ORIGINS" in p for p in problems)


def test_named_origins_are_fine():
    settings = FakeSettings(cors_allowed_origins="https://a.example.com,https://b.example.com")
    assert configuration_problems(settings) == []


def test_the_admin_password_from_the_documentation_is_refused():
    problems = configuration_problems(FakeSettings(admin_password="cargopilot123"))
    assert any("ADMIN_PASSWORD" in p for p in problems)


def test_no_admin_password_is_not_a_problem():
    """Zonder ADMIN_PASSWORD wordt er geen beheerder aangemaakt; dat is een
    geldige manier om te draaien nadat de eerste beheerder bestaat."""
    assert configuration_problems(FakeSettings(admin_password=None)) == []


def test_all_problems_are_reported_at_once():
    """Eén voor één laten ontdekken kost drie herstarts."""
    problems = configuration_problems(
        FakeSettings(app_secret_key="change-me", cors_allowed_origins="*",
                     admin_password="cargopilot123")
    )
    assert len(problems) == 3


# --- Alleen in productie -------------------------------------------------------

@pytest.mark.parametrize("environment", ["development", "dev", "local", "test", "testing"])
def test_development_may_use_a_fixed_known_key(environment):
    settings = FakeSettings(app_env=environment, app_secret_key="change-me",
                            cors_allowed_origins="*", admin_password="cargopilot123")
    assert configuration_problems(settings) == []
    verify_configuration(settings)


@pytest.mark.parametrize("environment", ["production", "prod", "", "staging", "acceptance"])
def test_anything_that_is_not_clearly_development_counts_as_production(environment):
    """De veilige kant: een omgevingsnaam die niemand herkent is productie.

    Andersom zou een typefout in APP_ENV de hele controle uitzetten zonder dat
    iemand het merkt.
    """
    assert is_production(environment)
    assert configuration_problems(FakeSettings(app_env=environment, app_secret_key="change-me"))


def test_the_real_settings_object_works_with_the_check():
    """De controle leest velden van Settings; die moeten blijven bestaan."""
    from app.core.config import Settings

    settings = Settings(app_env="production", app_secret_key="change-me",
                        cors_allowed_origins="*")
    problems = configuration_problems(settings)
    assert any("APP_SECRET_KEY" in p for p in problems)
    assert any("CORS_ALLOWED_ORIGINS" in p for p in problems)
