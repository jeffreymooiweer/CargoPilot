"""Welke talen de applicatie spreekt, en hoe zij een taal kiest.

Tot nu toe stond op elke plek waar tekst uit de configuratie kwam dezelfde
regel::

    return "en" if str(language).lower().startswith("en") else "nl"

Met twee talen klopte dat. Met een derde erbij zou "de" stilzwijgend
Nederlands opleveren: het scherm Duits, de waarschuwingen en de export
Nederlands. Erger nog, ``TEXTS[key][lang]`` was een KeyError zodra er iets
anders dan nl of en langskwam.

Daarom één plek. Een taal erbij is hier één regel, en de terugval is
uitgeschreven in plaats van per aanroep opnieuw bedacht.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: De talen die de interface aanbiedt. De frontend draagt dezelfde lijst in
#: ``src/i18n/language.ts``; ``test_languages.py`` bewaakt dat ze gelijk blijven.
#:
#: Frans staat er sinds v1.44.0 bij, en niet omdat het een grote taal is. Het
#: ADR, het RID en het ADN worden door de UNECE en de OTIF uitgegeven in het
#: Engels, het Frans en het Russisch, en de CMR- en CIM-vrachtbrief zijn van
#: oorsprong Franstalige documenten — de afkortingen zelf zijn Frans. Wie een
#: vrachtbrief opmaakt voor een Belgisch, Frans, Luxemburgs of Zwitsers traject
#: heeft de Franse benaming nodig, niet als beleefdheid maar omdat de
#: bevoegde autoriteit langs de weg die taal leest.
SUPPORTED = ("nl", "en", "de", "fr")

#: Nederlands is de taal waarin de gegevens het volledigst zijn: de
#: brontabellen en de toelichtingen zijn erin geschreven en de overige talen
#: zijn ervan afgeleid.
DEFAULT = "nl"

#: Waar naartoe wanneer een tekst in de gevraagde taal ontbreekt. Duits en Frans
#: vallen eerst op Engels terug: die lezer komt verder met Engels dan met
#: Nederlands. Nederlands blijft de laatste vangnetregel, want daar is altijd
#: iets.
_FALLBACKS: dict[str, tuple[str, ...]] = {
    "nl": ("nl", "en", "de", "fr"),
    "en": ("en", "nl", "de", "fr"),
    "de": ("de", "en", "nl", "fr"),
    "fr": ("fr", "en", "nl", "de"),
}


def normalise(language: Any) -> str:
    """De taalcode waarmee verder wordt gerekend.

    Accepteert wat een browser of API-aanroep oplevert — ``"de-AT"``,
    ``"EN_GB"``, ``None`` — en levert altijd een taal uit :data:`SUPPORTED`.
    """
    base = str(language or "").lower().replace("_", "-").split("-")[0]
    return base if base in SUPPORTED else DEFAULT


def pick(texts: Mapping[str, Any] | None, language: Any, default: Any = "") -> Any:
    """Haal tekst in de gevraagde taal uit een ``{nl, en, de}``-blokje.

    Een ontbrekende vertaling levert de eerstvolgende taal die er wél is; pas
    als geen enkele taal iets biedt komt ``default`` terug. Een leeg scherm is
    hier het slechtste antwoord: een veldnaam in de verkeerde taal kan de
    gebruiker nog lezen, een veld zonder naam niet.
    """
    if not isinstance(texts, Mapping):
        return default
    for candidate in _FALLBACKS[normalise(language)]:
        value = texts.get(candidate)
        if value not in (None, "", [], {}):
            return value
    return default
