"""Which languages the application speaks, and how it picks one.

Until now, every place that pulled text out of the configuration carried the
same line::

    return "en" if str(language).lower().startswith("en") else "nl"

With two languages that was correct. With a third it meant "de" silently
produced Dutch: the screen in German, the warnings and the export in Dutch.
Worse, ``TEXTS[key][lang]`` was a KeyError the moment anything other than nl
or en came past.

Hence one place. A language more is one line here, and the fallback is written
down instead of being reinvented at every call site.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: The languages the interface offers. The frontend carries the same list in
#: ``src/i18n/language.ts``; ``test_languages.py`` guards that they stay equal.
#:
#: French joined in v1.44.0, and not because it is a large language. ADR, RID
#: and ADN are published by UNECE and OTIF in English, French and Russian, and
#: the CMR and CIM waybills are French documents by origin — the abbreviations
#: themselves are French. Anyone preparing a waybill for a Belgian, French,
#: Luxembourgish or Swiss leg needs the French wording, not as a courtesy but
#: because the competent authority at the roadside reads that language.
SUPPORTED = ("nl", "en", "de", "fr")

#: Dutch is the language in which the data is most complete: the source tables
#: and the explanations are written in it and the other languages are derived
#: from it.
DEFAULT = "nl"

#: Where to go when a text is missing in the requested language. German and
#: French fall back to English first: that reader gets further with English
#: than with Dutch. Dutch stays the last safety net, because there is always
#: something there.
_FALLBACKS: dict[str, tuple[str, ...]] = {
    "nl": ("nl", "en", "de", "fr"),
    "en": ("en", "nl", "de", "fr"),
    "de": ("de", "en", "nl", "fr"),
    "fr": ("fr", "en", "nl", "de"),
}


def normalise(language: Any) -> str:
    """The language code everything downstream computes with.

    Accepts whatever a browser or an API call produces — ``"de-AT"``,
    ``"EN_GB"``, ``None`` — and always returns a language from :data:`SUPPORTED`.
    """
    base = str(language or "").lower().replace("_", "-").split("-")[0]
    return base if base in SUPPORTED else DEFAULT


def pick(texts: Mapping[str, Any] | None, language: Any, default: Any = "") -> Any:
    """Take text in the requested language out of a ``{nl, en, de}`` block.

    A missing translation yields the next language that does have something;
    only when no language offers anything does ``default`` come back. An empty
    screen is the worst answer here: a user can still read a field name in the
    wrong language, but not a field without a name.
    """
    if not isinstance(texts, Mapping):
        return default
    for candidate in _FALLBACKS[normalise(language)]:
        value = texts.get(candidate)
        if value not in (None, "", [], {}):
            return value
    return default
