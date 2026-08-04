"""In welke taal de juiste vervoersnaam op het document hoort.

De ADR-tabel in `seed/dg/un_numbers.json` draagt per UN-nummer twee officiële
benamingen: `name_en` en `name_de`. Tot nu toe pakte de app altijd de Engelse,
ook voor een Duitse gebruiker met een Duitse vrachtbrief — terwijl de officiële
Duitse benaming er gewoon naast stond.

Dat rechttrekken is niet simpelweg "vertaal mee met het scherm", want de
regelgeving zegt er per modaliteit iets anders over:

* **ADR 5.4.1.4.1** (weg), en langs dezelfde lijn RID en ADN: het
  vervoersdocument is gesteld in een officiële taal van het land van
  verzending, en als dat geen Duits, Engels of Frans is, bovendien in een van
  die drie. Een Duitse benaming op een CMR of CIM is dus juist wat een Duitse
  afzender nodig heeft.
* **IMDG 5.4.1.4.1** (zee) verlangt Engels, Frans of Spaans — geen Duits.
* **IATA DGR 8.1.2.1** (lucht) verlangt Engels.

"SALZSÄURE" op een Shipper's Declaration is daarmee geen vertaalkeuze maar een
geweigerde zending. Vandaar: Duits alleen wanneer er geen zee- of luchtprofiel
in het spel is. Bij een multimodale zending voldoet Engels aan alle drie, dus
dat blijft dan staan.
"""

from __future__ import annotations

from typing import Any

from app.core.languages import normalise

#: Profielen waarvoor de benaming Engels moet blijven.
ENGLISH_ONLY_PROFILES = {"IMDG", "IATA_DGR"}


def requires_english_name(profiles: list[str] | set[str] | None) -> bool:
    """Dwingt een van de gekozen profielen een Engelse benaming af?"""
    chosen = {str(profile).strip().upper() for profile in (profiles or [])}
    return bool(chosen & ENGLISH_ONLY_PROFILES)


def proper_shipping_name(
    entry: dict[str, Any],
    language: str = "nl",
    profiles: list[str] | set[str] | None = None,
) -> str:
    """De juiste vervoersnaam uit een ADR-vermelding, in hoofdletters.

    Duits wanneer de gebruiker Duits leest en geen enkel gekozen profiel
    Engels afdwingt; anders Engels. Er bestaat geen Nederlandse kolom in de
    ADR-tabel, dus Nederlands krijgt — net als voorheen — de Engelse benaming.
    """
    if normalise(language) == "de" and not requires_english_name(profiles):
        german = str(entry.get("name_de") or "").strip()
        if german:
            return german.upper()
    return str(entry.get("name_en") or entry.get("name_de") or "").strip().upper()


def is_german_name(entry: dict[str, Any], name: Any) -> bool:
    """Draagt deze tekst de Duitse benaming van deze vermelding?

    Gebruikt door de exportcontrole: wie eerst een wegdocument in het Duits
    opmaakt en er daarna een zeetraject bij zet, houdt de al ingevulde Duitse
    benaming — en die mag daar niet staan.
    """
    german = str(entry.get("name_de") or "").strip()
    english = str(entry.get("name_en") or "").strip()
    given = str(name or "").strip()
    if not german or not given:
        return False
    if german.casefold() == english.casefold():
        # Sommige vermeldingen luiden in beide talen hetzelfde; dan valt er
        # niets te melden.
        return False
    return given.casefold() == german.casefold()
