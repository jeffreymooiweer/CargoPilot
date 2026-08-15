"""Recognise dangerous goods by name in free-text cargo lines.

Whoever types "20 vaten benzine" has told the application everything it needs
to find UN 1203 — the four-language name index has known the substance all
along — but until v1.98.0 only a literal "UN 1203" in the text was recognised.
This module closes that gap, and it does so as a *suggestion*: recognition from
free text can be wrong, so nothing is set silently. The interface shows what
was recognised and the user confirms or rejects it.

What enters the lexicon is measured, not guessed. Every language column of
table A prints the proper shipping name in capitals and its qualifiers in lower
case ("ZWAVELZUUR met meer dan 51% zuur", "SULPHURIC ACID with more than 51 %
acid"), and that typography is the boundary this module relies on: the capital
part is the name, and only the name becomes a lexicon key. Nothing shorter is
derived from it — "ALUMINIUM, GESMOLTEN" is printed in capitals as a whole, so
"aluminium" on its own matches nothing, and an aluminium tube stays what it is.
No trade names or synonyms are invented either: a word matches only if some
edition prints it as (part of) the name.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Any

from app.services.dg import database
from app.services.dg.database import get_un_entries
from app.services.dg.names_de import german_names
from app.services.dg.names_en import english_names
from app.services.dg.names_fr import french_names
from app.services.dg.names_nl import dutch_names
from app.services.dg.naming import proper_shipping_name

#: How the four columns join alternative names ("MOTOR SPIRIT or GASOLINE or
#: PETROL"). Lower case in print; matched case-insensitively because the
#: fallback fields carry the joined form in capitals.
_SEPARATORS = {
    "nl": re.compile(r"\s+of\s+", re.IGNORECASE),
    "en": re.compile(r"\s+or\s+", re.IGNORECASE),
    "de": re.compile(r"\s+oder\s+", re.IGNORECASE),
    "fr": re.compile(r"\s+ou\s+", re.IGNORECASE),
}

_PARENS = re.compile(r"\([^()]*\)")

#: A key this many UN numbers share names nothing in particular; suggesting
#: all of them would be noise, so such a key is dropped from the lexicon.
_TOO_GENERIC = 5

#: The most candidates a single line is allowed to raise. More than this means
#: the text was too vague for the suggestion to help.
_MAX_CANDIDATES = 5


def _strip_parens(text: str) -> str:
    """Remove parenthetical qualifiers, nested ones included."""
    while True:
        stripped = _PARENS.sub(" ", text)
        if stripped == text:
            return text
        text = stripped


def _caps_name(alternative: str) -> str:
    """The leading run of capital-printed words: the name proper.

    Stops at the first lower-case word, which is where the book switches from
    the name to its qualifier. Commas and digits inside the capital run belong
    to the name ("STOOKOLIE, LICHT", "N.O.S.").
    """
    words = _strip_parens(alternative).split()
    kept: list[str] = []
    for word in words:
        letters = [c for c in word if c.isalpha()]
        if letters and word != word.upper():
            break
        kept.append(word)
    return " ".join(kept).strip(" ,")


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return [t for t in re.split(r"[^a-z0-9]+", text) if t]


def _names_for(un: str, entry: dict[str, Any]) -> list[tuple[str, str]]:
    """(language, name string) pairs for one UN number, read columns first."""
    pairs: list[tuple[str, str]] = []
    for language, from_column, fallback_key in (
        ("nl", dutch_names(un), "name_nl"),
        ("en", english_names(un), "name_en"),
        ("de", german_names(un), "name_de"),
        ("fr", french_names(un), ""),
    ):
        if from_column:
            pairs.extend((language, name) for name in from_column)
        elif fallback_key and entry.get(fallback_key):
            pairs.append((language, str(entry[fallback_key])))
    return pairs


@lru_cache(maxsize=1)
def _lexicon() -> dict[str, list[tuple[tuple[str, ...], tuple[str, ...]]]]:
    """First token → [(key tokens, UN numbers)], longest keys first."""
    keys: dict[tuple[str, ...], set[str]] = {}
    seen: set[str] = set()
    for entry in database._load_un():
        un = entry["un"]
        # A withdrawn entry may still be looked up, but it must not be
        # suggested for a new consignment.
        if un in seen or entry.get("withdrawn_in"):
            continue
        seen.add(un)
        for language, name in _names_for(un, entry):
            for alternative in _SEPARATORS[language].split(name):
                tokens = tuple(_tokens(_caps_name(alternative)))
                if not tokens or len("".join(tokens)) < 4:
                    continue
                keys.setdefault(tokens, set()).add(un)

    index: dict[str, list[tuple[tuple[str, ...], tuple[str, ...]]]] = {}
    for tokens, uns in keys.items():
        if len(uns) > _TOO_GENERIC:
            continue
        index.setdefault(tokens[0], []).append((tokens, tuple(sorted(uns))))
    for bucket in index.values():
        bucket.sort(key=lambda item: -len(item[0]))
    return index


def detect_name_candidates(
    description: str, language: str = "nl"
) -> list[dict[str, Any]]:
    """UN candidates recognised by name, for the interface to propose.

    Whole words only, longest name first, so "benzinemotor" is no petrol and
    "stookolie licht" is not read as two matches. Returns at most
    ``_MAX_CANDIDATES`` candidates; an empty list where the text is too vague
    for a suggestion to mean anything.
    """
    tokens = _tokens(description or "")
    if not tokens:
        return []
    index = _lexicon()
    matches: list[tuple[int, int, tuple[str, ...]]] = []
    for start, token in enumerate(tokens):
        for key, uns in index.get(token, ()):
            if tuple(tokens[start:start + len(key)]) == key:
                matches.append((start, len(key), uns))
                break  # longest key at this position; shorter ones are inside it

    # A match inside a longer match is that longer name's own words.
    kept: list[tuple[int, int, tuple[str, ...]]] = []
    for start, length, uns in matches:
        if any(o_start <= start and start + length <= o_start + o_length
               for o_start, o_length, _ in matches
               if (o_start, o_length) != (start, length)):
            continue
        kept.append((start, length, uns))

    ordered: list[str] = []
    for _start, _length, uns in kept:
        for un in uns:
            if un not in ordered:
                ordered.append(un)
    if not ordered or len(ordered) > _MAX_CANDIDATES:
        return []

    candidates = []
    for un in ordered:
        entries = get_un_entries(un)
        if not entries:
            continue
        entry = entries[0]
        candidates.append({
            "un": un,
            "name": proper_shipping_name(entry, language),
            "class": str(entry.get("class") or ""),
            "packing_group": str(entry.get("packing_group") or ""),
        })
    return candidates
