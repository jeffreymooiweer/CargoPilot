"""What is written *about* the app is English too, not only the comments.

`test_source_language.py` keeps the comments and docstrings English, and it does
that by throwing away every quoted string first — because Dutch inside a string
literal is usually data. The import format really is
`Stalen hoekprofiel 80x80x8x6000 | 8 | stuks`, and a guard that fired on it
would be switched off within the week.

That exemption turned out to be a hole. Three kinds of prose live in strings and
in Markdown, are read by exactly the people the translation was for, and passed
straight through:

- **The changelog.** It was English until v1.49.0, when ten releases' worth of
  Dutch entries went into it — mine, because the person I was talking to writes
  Dutch. Nobody reading the repository does.
- **Provenance metadata in the seeds.** The `_comment`, `source` and
  `cross_check` fields say where a table came from and how it was checked. They
  are the closest thing this project has to a chain of custody, and they are for
  a reader, not for the code.
- **What the scripts print.** `--help` and the self-check output of
  `scripts/extract_*.py` are the interface of a tool a contributor runs.

What stays exempt is what a *user* reads: the `{nl, en, de, fr}` blocks, the
goods names, the Dutch proper shipping names out of ADR Table A, the Dutch
disclaimer. Those are the product. The rule is the same one as in the other
file — the interface speaks four languages, the repository speaks one — applied
where that file could not look.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from tests.test_source_language import DUTCH

ROOT = Path(__file__).resolve().parents[2]

#: Keys under which prose about the data lives, rather than the data itself.
#: Anything beginning with an underscore is metadata by this repository's own
#: convention; the rest are named because they carry sentences.
META_KEYS = ("source", "cross_check", "note", "comment", "errata", "covers")

#: A value nested anywhere under one of these keys is a translation and is left
#: alone — including suffixed forms such as `changes_nl` and `note_de`.
LANGUAGES = {"nl", "en", "de", "fr"}

#: Seeds and configuration that carry provenance metadata.
DATA_FILES = ("backend/seed", "backend/app/config")


def _is_translation(trail: list[str]) -> bool:
    return any(key in LANGUAGES or key.rsplit("_", 1)[-1] in LANGUAGES
               for key in trail)


def _is_metadata(key: str) -> bool:
    return key.startswith("_") or key in META_KEYS


def metadata_strings(data: object, trail: list[str] | None = None):
    """Yield (path, text) for every prose-metadata string in a JSON tree."""
    trail = trail or []
    if isinstance(data, dict):
        for key, value in data.items():
            yield from metadata_strings(value, trail + [key])
    elif isinstance(data, list):
        for item in data:
            yield from metadata_strings(item, trail)
    elif isinstance(data, str) and trail:
        if _is_translation(trail) or not _is_metadata(trail[-1]):
            return
        yield ".".join(trail), data


def json_files() -> list[Path]:
    found: list[Path] = []
    for folder in DATA_FILES:
        found.extend(sorted((ROOT / folder).rglob("*.json")))
    return found


def printed_strings(path: Path):
    """Yield (line, text) for what a script prints and for its --help text.

    Read from the syntax tree rather than with a regular expression, so an
    f-string split over four lines is four separate pieces of text and each one
    is judged on its own.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        wanted: list[ast.AST] = []
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            wanted.extend(node.args)
        wanted.extend(kw.value for kw in node.keywords if kw.arg == "help")
        for argument in wanted:
            for part in ast.walk(argument):
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    yield part.lineno, part.value


def changelog_prose() -> list[tuple[int, str]]:
    """The changelog with its code taken out.

    Fenced blocks and inline code spans are quoted material — a Dutch error
    message the app really produces is in there as an example, and that is the
    point of quoting it. Spans are removed from the whole document at once
    because one of them runs over two lines; the newlines are kept so the line
    numbers still name the right line.
    """
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    text = re.sub(r"`[^`]*`", lambda m: "\n" * m.group(0).count("\n"), text)
    lines: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            lines.append((number, line))
    return lines


def test_the_changelog_is_english():
    """Ten releases went in in Dutch before anyone noticed; this is the notice."""
    offenders = [f"CHANGELOG.md:{number}: {line.strip()[:90]}"
                 for number, line in changelog_prose() if DUTCH.search(line)]
    assert offenders == [], (
        "Dutch in the changelog. The releases are read by whoever picks up this "
        "repository.\n" + "\n".join(offenders[:20])
    )


@pytest.mark.parametrize("folder", DATA_FILES)
def test_the_provenance_metadata_is_english(folder: str):
    """Where a table came from, and how it was checked, is prose for a reader."""
    offenders: list[str] = []
    for path in json_files():
        if not str(path).startswith(str(ROOT / folder)):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:  # pragma: no cover - a broken seed fails elsewhere
            continue
        for where, text in metadata_strings(data):
            if DUTCH.search(text):
                offenders.append(f"{path.relative_to(ROOT)} {where}: {text[:80]}")

    assert offenders == [], (
        "Dutch provenance metadata. The `{nl, en, de, fr}` blocks and the goods "
        "names are exempt — this is the prose about the data.\n"
        + "\n".join(offenders[:20])
    )


def test_what_the_scripts_print_is_english():
    """`--help` and the self-check output are the interface of these tools."""
    offenders: list[str] = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        for line, text in printed_strings(path):
            if DUTCH.search(text):
                offenders.append(f"{path.relative_to(ROOT)}:{line}: {text[:80]}")

    assert offenders == [], (
        "Dutch in what a script prints.\n" + "\n".join(offenders[:20])
    )


def test_the_scan_reaches_the_files_it_claims_to():
    """Three assertions that would each pass just as well on an empty scan."""
    assert len(changelog_prose()) > 1000
    metadata = [text for path in json_files()
                for _, text in metadata_strings(json.loads(path.read_text(encoding="utf-8")))]
    assert len(metadata) > 20, f"only {len(metadata)} metadata strings seen"
    printed = [t for path in sorted((ROOT / "scripts").glob("*.py"))
               for _, t in printed_strings(path)]
    assert len(printed) > 100, f"only {len(printed)} printed strings seen"


def test_the_translation_blocks_stay_out_of_it():
    """The exemption, asserted rather than assumed.

    Without this the guard could be tightened one day into something that fires
    on `"nl": "Gescheiden van (separated from)"` — and the fix for that is to
    delete the Dutch a user is meant to read.
    """
    assert _is_translation(["messages", "nl"])
    assert _is_translation(["amended_un_numbers", "1010", "changes_nl"])
    assert _is_translation(["new_stowage_codes", "SW31", "assigned_to_note_de"])
    assert not _is_translation(["cross_check", "index", "examples"])
    assert not _is_translation(["_comment"])
