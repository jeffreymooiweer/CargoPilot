"""Weigeren te starten met een configuratie die de app open zet.

`APP_SECRET_KEY` tekent de JWT waarmee een gebruiker is ingelogd. De
standaardwaarde staat in deze repository, dus een installatie die hem nooit
heeft gezet draait op een sleutel die iedereen kan opzoeken — en wie de sleutel
heeft, schrijft zelf een geldig token voor de beheerder. Dat is geen
hardening-punt maar een open voordeur.

Zoiets stil doorlaten en er hooguit een regel over loggen werkt niet: logs
worden niet gelezen en de app blijft gewoon draaien. Daarom stopt hij hier,
mét de opdracht die het oplost.

De controle geldt alleen in productie. Bij ontwikkelen en testen is een vaste,
bekende sleutel juist handig; `APP_ENV=development` (of `test`, of `local`)
zet de controle uit.
"""
from __future__ import annotations

import secrets

# Waarden die in deze repository, in de documentatie of in de voorbeelden staan.
# Alles wat hier in staat is publiek en dus geen geheim.
PUBLISHED_SECRETS = {
    "change-me",
    "changeme",
    "dev-secret",
    "ci-secret",
    "secret",
    "cargopilot",
    "please-change",
    "your-secret-key",
    # Staat letterlijk in .env.example en is lang genoeg om langs de
    # lengtecontrole te glippen; wie het bestand kopieert is niet veilig.
    "change-me-to-a-long-random-string",
}

# Idem voor het eerste beheerderswachtwoord: dit staat in docs/development.md en
# in AGENTS.md als voorbeeld.
PUBLISHED_ADMIN_PASSWORDS = {
    "cargopilot123",
    "admin",
    "password",
    "changeme",
    "change-me",
}

# Onder deze lengte is een HS256-sleutel te kort om zinvol te zijn.
MINIMUM_SECRET_LENGTH = 32

DEVELOPMENT_ENVIRONMENTS = {"dev", "develop", "development", "local", "test", "testing"}


class InsecureConfiguration(RuntimeError):
    """De applicatie is zo ingesteld dat starten onverantwoord is."""


def is_production(app_env: str) -> bool:
    return str(app_env or "").strip().lower() not in DEVELOPMENT_ENVIRONMENTS


def suggested_secret() -> str:
    """Een bruikbare sleutel, zodat de foutmelding meteen de oplossing bevat."""
    return secrets.token_urlsafe(48)


def configuration_problems(settings) -> list[str]:
    """Wat er mis is, in gewone taal en met wat eraan te doen is.

    Leeg betekent: veilig genoeg om te starten. Er wordt niets gerepareerd —
    raden wat iemand bedoeld had is bij beveiliging de verkeerde reflex.
    """
    if not is_production(settings.app_env):
        return []

    problems: list[str] = []
    secret = str(settings.app_secret_key or "")

    if secret.strip().lower() in PUBLISHED_SECRETS:
        problems.append(
            f"APP_SECRET_KEY staat nog op de gepubliceerde standaardwaarde "
            f"({secret!r}). Die sleutel tekent de inlogtokens: wie hem kent kan "
            f"zelf een token voor de beheerder maken. Zet er een eigen waarde "
            f"voor in de plaats, bijvoorbeeld:\n"
            f"    APP_SECRET_KEY={suggested_secret()}"
        )
    elif len(secret.strip()) < MINIMUM_SECRET_LENGTH:
        problems.append(
            f"APP_SECRET_KEY is {len(secret.strip())} tekens lang; minimaal "
            f"{MINIMUM_SECRET_LENGTH} is nodig om de inlogtokens niet te laten "
            f"raden. Bijvoorbeeld:\n    APP_SECRET_KEY={suggested_secret()}"
        )

    if settings.cors_allowed_origins.strip() == "*":
        problems.append(
            "CORS_ALLOWED_ORIGINS staat op '*' terwijl de API met cookies werkt. "
            "Daarmee mag elke website namens een ingelogde gebruiker verzoeken "
            "doen. Noem de adressen waarop je CargoPilot bereikt, bijvoorbeeld:\n"
            "    CORS_ALLOWED_ORIGINS=https://cargopilot.example.com"
        )

    password = str(settings.admin_password or "")
    if password and password.strip().lower() in PUBLISHED_ADMIN_PASSWORDS:
        problems.append(
            "ADMIN_PASSWORD staat op een wachtwoord dat in de documentatie van "
            "dit project staat. Kies er een eigen."
        )

    return problems


def verify_configuration(settings) -> None:
    """Stoppen als de configuratie de app open zet.

    Wordt bij het opbouwen van de applicatie aangeroepen, dus vóórdat er ook
    maar één verzoek beantwoord kan worden.
    """
    problems = configuration_problems(settings)
    if not problems:
        return
    raise InsecureConfiguration(
        "CargoPilot start niet met deze instellingen:\n\n"
        + "\n\n".join(f"  • {problem}" for problem in problems)
        + "\n\nZie docs/configuration.md. Bij ontwikkelen: APP_ENV=development."
    )
