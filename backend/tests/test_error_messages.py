"""An error is the one text a user reads in the wrong language and cannot ignore.

Everything on screen was translated into four languages, and the errors were
not. They were written straight into the ``raise`` as Dutch sentences, so a
German user uploading an empty file, or a French one asking after a UN number
the ADR table does not hold, was told so in a language they may not read. It is
the kind of gap nobody reports, because it only shows up once something has
already gone wrong — and at that moment the user is least able to work out what
happened.

The fix is a code per message. The server does not translate: it raises deep in
a service that has no idea who is asking, and the language belongs to the
screen. It sends ``{"code", "message", "params"}``; the interface looks the code
up in its own language files and falls back to the English ``message`` when it
does not know it.

Three things have to hold for that to work, and each is a test here:

1. **Every code has a translation in every language.** A missing key falls back
   to English, which works but quietly undoes the whole exercise.
2. **The parameters match.** A sentence with ``{{limit_mb}}`` in the Dutch and
   nothing in the German is a German sentence with a number missing from it.
3. **No message is written in Dutch at the raise site any more.** Otherwise the
   next one added slips straight back past all of this.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from app.core.messages import MESSAGES, error, text

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "frontend" / "src" / "i18n"
LANGUAGES = ("nl", "en", "de", "fr")


def bundle(language: str) -> dict:
    return json.loads((I18N / f"{language}.json").read_text(encoding="utf-8"))


def translation(language: str, code: str) -> str | None:
    """The `errors.<code>` entry, where the code is a dotted path of its own."""
    node = bundle(language).get("errors", {})
    for part in code.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def placeholders(sentence: str) -> set[str]:
    """The interpolation names in a sentence, in either notation.

    Python uses `{limit_mb}` and i18next uses `{{limit_mb}}`; both reduce to the
    same set of names, which is what has to match.
    """
    return set(re.findall(r"\{\{?(\w+)\}?\}", sentence))


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_message_code_is_translated(language: str):
    """A code without a key silently serves English and looks like it works."""
    missing = sorted(code for code in MESSAGES if translation(language, code) is None)
    assert missing == [], f"{language}.json is missing errors for: {missing}"


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_placeholders_survive_the_translation(language: str):
    """A number that falls out of a sentence takes the sentence's point with it."""
    wrong: list[str] = []
    for code, english in MESSAGES.items():
        translated = translation(language, code)
        if translated is None:
            continue
        if placeholders(translated) != placeholders(english):
            wrong.append(
                f"{code}: {language} has {sorted(placeholders(translated))}, "
                f"English has {sorted(placeholders(english))}"
            )
    assert wrong == [], "\n".join(wrong)


def test_no_translation_is_left_as_the_english_original():
    """A copied English line in the Dutch file is not a translation.

    Some are legitimately identical — a code, a unit — so this only demands that
    the *majority* differ, the same test the goods catalogue carries.
    """
    identical = [
        code
        for code, english in MESSAGES.items()
        if translation("nl", code) == english
    ]
    assert len(identical) < len(MESSAGES) / 2, f"suspiciously many untranslated: {identical}"


def test_the_english_fallback_interpolates_its_parameters():
    assert text("import.file_too_large", limit_mb=10) == "The file is larger than 10 MB"


def test_an_unknown_code_does_not_turn_a_handled_error_into_a_crash():
    """The code itself is still usable: the interface translates on it."""
    assert text("nothing.like.this") == "nothing.like.this"


def test_the_error_carries_the_code_and_the_parameters():
    """The interface needs all three parts, so all three have to travel."""
    raised = error(413, "import.file_too_large", limit_mb=10)

    assert raised.status_code == 413
    assert raised.detail["code"] == "import.file_too_large"
    assert raised.detail["message"] == "The file is larger than 10 MB"
    assert raised.detail["params"] == {"limit_mb": 10}


#: Where a message to the user is written. Anything else — a log line, a
#: docstring, a comment — is for whoever runs the installation and stays English.
USER_FACING = (
    ROOT / "backend" / "app" / "api" / "routes",
    ROOT / "backend" / "app" / "schemas",
    ROOT / "backend" / "app" / "services",
)

DUTCH = re.compile(
    r"\b(het|een|niet|geen|bestand|bestandsnaam|leeg|gevonden|onbekend|ongeldig"
    r"|groter|kleiner|regels|regel|rijen|kolommen|tekens|zonder|hoeveelheid"
    r"|omschrijving|ontbreekt|bevat|moet|mag|wordt|zijn|nummer)\b",
    re.IGNORECASE,
)


def message_strings(path: Path):
    """Every literal handed to a user: an HTTP detail, or a raised error text."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name not in {"HTTPException", "ApiError", "ValueError", "PydanticCustomError"}:
            continue
        for argument in list(node.args) + [kw.value for kw in node.keywords]:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                yield node.lineno, argument.value


def test_no_message_to_the_user_is_written_in_dutch():
    """The guard that keeps the next one from slipping back in.

    It reads the raise sites rather than the message catalogue, because that is
    where the shortcut is taken: a sentence typed straight into `HTTPException`
    never passes through `app.core.messages` at all.
    """
    offenders: list[str] = []
    for folder in USER_FACING:
        for path in sorted(folder.rglob("*.py")):
            if "__pycache__" in str(path):
                continue
            for line, value in message_strings(path):
                if DUTCH.search(value):
                    offenders.append(f"{path.relative_to(ROOT)}:{line}: {value[:70]}")
    assert offenders == [], (
        "Messages to the user must go through app.core.messages so the interface "
        "can translate them.\n" + "\n".join(offenders)
    )
