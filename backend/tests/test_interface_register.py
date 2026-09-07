"""The interface addresses its user one way, and only one way.

For a long time it did both at once. The Dutch introduction on the
transport-mode chooser addressed the reader formally; the two-factor notice a
couple of centimetres below it addressed them informally. One screen, two
registers — and nobody notices that while writing one string at a time, which
is exactly why it needs a guard rather than a rule somebody remembers.

The owner chose the formal one, so:

* **Dutch** is *u* and *uw* — never *je*, *jij*, *jou*, *jouw* or *jullie*.
* **German** is *Sie* and *Ihr* — never *du*, *dein* or *dich*.
* **French** was already *vous* throughout, and this keeps it that way.
* **English** has no such distinction and is not checked.

What is *not* checked is the rest of the repository. Comments, the changelog
and this file speak to whoever picks the project up, not to a user, and
`test_repository_language.py` already has an opinion about those.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "frontend" / "src" / "i18n"

#: Per language, the informal forms and the formal ones they should have been.
#: Word boundaries on both sides, so *Sendungen* is not a hit for *du* and
#: *tabellen* is not one for *ta*.
INFORMAL = {
    "nl": (r"\b(?:je|jij|jou|jouw|jullie|jezelf)\b", "u / uw"),
    "de": (r"\b(?:du|dich|dir|dein(?:e|em|en|er|es)?)\b", "Sie / Ihr"),
    "fr": (r"\b(?:tu|toi|ton|ta|tes)\b", "vous / votre"),
}


def strings(node: object, trail: str = ""):
    """Yield (key path, text) for every leaf of a translation file."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from strings(value, f"{trail}.{key}" if trail else key)
    elif isinstance(node, str):
        yield trail, node


@pytest.mark.parametrize("language", sorted(INFORMAL))
def test_the_interface_addresses_its_user_formally(language: str):
    pattern, formal = INFORMAL[language]
    catalogue = json.loads((I18N / f"{language}.json").read_text(encoding="utf-8"))
    offenders = [
        f"{key}: {text}"
        for key, text in strings(catalogue)
        if re.search(pattern, text, re.IGNORECASE)
    ]
    assert offenders == [], (
        f"Informal address in the {language} interface, which speaks {formal}. "
        "One screen saying both is what this exists to stop.\n  "
        + "\n  ".join(offenders)
    )


def test_the_guard_recognises_the_informal_when_it_sees_it():
    """A guard that cannot fail is not a guard.

    The pattern is what does the work here, so it is the pattern that is
    tested — against the sentences this rule was written for, and against the
    formal ones it must leave alone."""
    caught = {
        "nl": "Je account heeft nog geen tweestapsverificatie.",
        "de": "Wo du aufgehört hast.",
        "fr": "Ce que tu saisis ici.",
    }
    allowed = {
        "nl": "Uw account heeft nog geen tweestapsverificatie. Stel hem in zolang u kunt.",
        "de": "Wo Sie aufgehört haben. Ihre Eingabe ist mitgekommen.",
        "fr": "Ce que vous saisissez ici est repris à votre étape.",
    }
    for language, (pattern, _) in INFORMAL.items():
        assert re.search(pattern, caught[language], re.IGNORECASE), language
        assert not re.search(pattern, allowed[language], re.IGNORECASE), language


def test_every_language_the_interface_speaks_is_accounted_for():
    """English has no formal and informal *you*, so it has no rule — but a
    fifth language appearing without one would slip through unnoticed."""
    present = {path.stem for path in I18N.glob("*.json")}
    assert present == set(INFORMAL) | {"en"}, present
