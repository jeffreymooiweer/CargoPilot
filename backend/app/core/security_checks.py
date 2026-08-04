"""Zorgen dat de app veilig start — niet dat hij niet start.

`APP_SECRET_KEY` tekent de JWT waarmee een gebruiker is ingelogd. De
standaardwaarde staat in deze repository, dus een installatie die hem nooit
heeft gezet draait op een sleutel die iedereen kan opzoeken, en wie de sleutel
heeft schrijft zelf een geldig token voor de beheerder. Dat is een open
voordeur en geen schoonheidsfoutje.

**Wat hier eerst stond, en waarom dat fout was.** Vanaf v1.25.0 weigerde
CargoPilot in dat geval te starten. De redenering — een waarschuwing in een log
leest niemand — klopte; de uitwerking niet. De standaardwaarden van deze
applicatie zíjn `APP_SECRET_KEY=change-me` en `CORS_ALLOWED_ORIGINS=*`, en de
Unraid-sjabloon laat de sleutel leeg. Daarmee crashte elke installatie die die
twee niet uit zichzelf had ingevuld, meteen bij het opstarten, in een container
die zo snel afsloot dat de melding niet eens te lezen was. De beveiliging werd
er niet beter van: de app was gewoon weg.

Een self-hosted applicatie met een eigen gegevensmap hoeft dit ook niet aan de
gebruiker te vragen. Zij maakt zelf een sleutel, bewaart die naast haar
database en gebruikt hem voortaan. Dat is veiliger dan wat er stond
(willekeurig in plaats van gepubliceerd), het kost de gebruiker niets, en de
sleutel overleeft een herstart omdat hij op de gemounte map staat.

Wat overblijft is melden. CORS wijd open of een beheerderswachtwoord uit de
documentatie is het waard om te zeggen, maar geen reden om de deur op slot te
gooien met de gebruiker erbuiten.
"""
from __future__ import annotations

import logging
import secrets
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

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

#: Naast de database, op de gemounte gegevensmap, zodat de sleutel een herstart
#: en het opnieuw aanmaken van de container overleeft.
SECRET_KEY_FILENAME = "secret_key"


def is_production(app_env: str) -> bool:
    return str(app_env or "").strip().lower() not in DEVELOPMENT_ENVIRONMENTS


def suggested_secret() -> str:
    return secrets.token_urlsafe(48)


def is_usable_secret(secret: str) -> bool:
    """Kan hiermee een token worden getekend dat niet te raden of op te zoeken is?"""
    value = str(secret or "").strip()
    if value.lower() in PUBLISHED_SECRETS:
        return False
    return len(value) >= MINIMUM_SECRET_LENGTH


def _read_stored_secret(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _store_secret(path: Path, secret: str) -> bool:
    """Bewaar de sleutel, alleen leesbaar voor de eigenaar. True als het lukte."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secret + "\n", encoding="utf-8")
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return True
    except OSError as error:
        # Op Unraid is /data wel eens niet schrijfbaar. Dat mag het opstarten
        # niet tegenhouden; het kost alleen de duurzaamheid van de sleutel.
        logger.warning("Kon de sleutel niet opslaan in %s: %s", path, error)
        return False


def ensure_secret_key(settings) -> str:
    """Lever een bruikbare ondertekeningssleutel, desnoods door er een te maken.

    Volgorde: wat is ingesteld, anders wat er eerder is bewaard, anders een
    nieuwe. De ingestelde waarde wint altijd wanneer zij deugt, zodat wie zijn
    sleutel bewust beheert daar de baas over blijft.
    """
    configured = str(settings.app_secret_key or "").strip()
    if is_usable_secret(configured):
        return configured

    path = Path(settings.data_dir) / SECRET_KEY_FILENAME
    stored = _read_stored_secret(path)
    if is_usable_secret(stored):
        logger.info(
            "APP_SECRET_KEY niet ingesteld; de bewaarde sleutel uit %s wordt gebruikt.", path
        )
        return stored

    generated = suggested_secret()
    if _store_secret(path, generated):
        logger.warning(
            "APP_SECRET_KEY was niet ingesteld of te kort. Er is een sleutel "
            "gemaakt en bewaard in %s. Wil je hem zelf beheren, zet dan "
            "APP_SECRET_KEY in de omgeving; die gaat dan voor.",
            path,
        )
    else:
        logger.warning(
            "APP_SECRET_KEY was niet ingesteld of te kort en de gemaakte sleutel "
            "kon niet worden bewaard. De app draait veilig, maar iedereen moet "
            "na een herstart opnieuw inloggen. Zet APP_SECRET_KEY in de omgeving "
            "of maak %s schrijfbaar.",
            path.parent,
        )
    return generated


def configuration_warnings(settings) -> list[str]:
    """Wat er los van de sleutel nog aandacht verdient, in gewone taal.

    Dit zijn meldingen en geen weigeringen. Ze zeggen wat er open staat en wat
    eraan te doen is; de gebruiker beslist zelf of dat in zijn opstelling erg is
    — achter een reverse proxy op één domein is CORS bijvoorbeeld niet in beeld.
    """
    if not is_production(settings.app_env):
        return []

    warnings: list[str] = []

    if settings.cors_allowed_origins.strip() == "*":
        warnings.append(
            "CORS_ALLOWED_ORIGINS staat op '*'. Browsers weigeren dat te "
            "combineren met cookies, dus een aanroep vanaf een andere website "
            "werkt niet — maar noem liever de adressen waarop je CargoPilot "
            "bereikt:\n    CORS_ALLOWED_ORIGINS=https://cargopilot.example.com"
        )

    password = str(settings.admin_password or "")
    if password and password.strip().lower() in PUBLISHED_ADMIN_PASSWORDS:
        warnings.append(
            "ADMIN_PASSWORD staat op een wachtwoord dat in de documentatie van "
            "dit project staat. Kies er een eigen, en verander het na de eerste "
            "keer inloggen."
        )

    return warnings


def apply_security_configuration(settings) -> list[str]:
    """Maak de instellingen veilig genoeg om mee te starten, en meld de rest.

    Wordt bij het opbouwen van de applicatie aangeroepen, dus vóórdat er ook
    maar één verzoek beantwoord kan worden. Retourneert de meldingen, zodat een
    test ze kan lezen zonder in het log te hoeven kijken.
    """
    settings.app_secret_key = ensure_secret_key(settings)

    warnings = configuration_warnings(settings)
    for warning in warnings:
        logger.warning("Aandachtspunt in de configuratie: %s", warning)
    return warnings
