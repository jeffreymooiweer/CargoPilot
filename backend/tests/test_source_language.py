"""The interface speaks four languages; the source speaks one.

Comments and docstrings were Dutch across this repository for a long time, and
that was a defensible choice while one person wrote all of it. It stopped being
one the moment the project became something other people read: a docstring that
explains *why* a check exists is worth nothing to a reader who cannot read it,
and this project puts a great deal of its reasoning in exactly those docstrings.

v1.46.0 translated roughly 3,000 lines of comment across `backend/`,
`frontend/`, `scripts/` and the workflows. This test is what keeps them
translated. Without it the next contribution adds a Dutch comment, the one after
that adds three, and in a year the work has to be done again.

**Scope, deliberately.** Only comments and docstrings. Everything a *user* reads
stays translated — the language files, the seed labels, the regulatory texts.
Dutch inside a string literal is data, not prose, and is not flagged: the import
format is `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks` and the AVC form's own
column is called `gewicht in kg`.

**The word list is function words on purpose.** Words such as the Dutch article
and the third-person verb forms cannot plausibly appear in an English sentence,
while a noun can perfectly well be quoted in one. Words that collide with English
are left out — "door" is a Dutch preposition and an English noun, and the back
door of a CI pipeline is a phrase this repository actually uses. False positives
would be worse than a few missed words: a guard that cries wolf gets switched off.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Directories whose comments have to be English, with the file types in them.
SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("backend/app", ("*.py",)),
    ("backend/tests", ("*.py",)),
    ("scripts", ("*.py",)),
    ("frontend/src", ("*.ts", "*.tsx")),
    (".github/workflows", ("*.yml",)),
)

#: Dutch function words. Nouns are deliberately absent — those get quoted in
#: English comments as data ("stuks", "beton", "gewicht in kg") and would make
#: this guard fire on correct lines.
DUTCH = re.compile(
    r"\b(het|een|niet|wordt|worden|werd|zijn|deze|dit|zodat|omdat|dus|ook|maar|geen"
    r"|naar|aan|als|nog|alleen|elke|hier|daar|waarom|moet|moeten|kan|kunnen|heeft"
    r"|hebben|staat|staan|komt|komen|gaat|gaan|welke|hun|waarbij|waardoor|waarmee"
    r"|waarvan|waarop|vandaar|daarom|zoals|wanneer|terwijl|tenzij|hoewel|zonder"
    r"|iets|niets|altijd|nooit|vaak|soms|liever|erger|beter|verder|eerst|opnieuw"
    r"|zelf|samen|tussen|onder|boven|zolang|toch|slechts|echter|namelijk)\b",
    re.IGNORECASE,
)

DOC_START = re.compile(r'^\s*(?:[rbfuRBFU]{0,2})("""|\'\'\')')


def _strip_strings(line: str) -> str:
    """Remove quoted text, so data in a string cannot trip the word list."""
    return re.sub(r"""(["'])(?:\\.|(?!\1).)*\1""", "", line)


def comment_lines(path: Path):
    """Yield (line number, prose) for every comment and docstring line."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix
    open_doc: str | None = None
    open_block = False

    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()

        if suffix == ".py":
            if open_doc:
                yield number, line
                if open_doc in stripped:
                    open_doc = None
                continue
            match = DOC_START.match(line)
            if match:
                quote = match.group(1)
                yield number, line
                if quote not in line[match.end():]:
                    open_doc = quote
                continue
            if stripped.startswith("#"):
                yield number, line
            elif "#" in _strip_strings(line):
                yield number, _strip_strings(line).split("#", 1)[1]
        elif suffix in (".ts", ".tsx"):
            if open_block:
                yield number, line
                if "*/" in stripped:
                    open_block = False
                continue
            # `{/* … */}` is how a comment is written inside JSX, and it is the
            # form the panels use. Reading only `/*` at the start of a line
            # missed every one of them; three Dutch ones survived v1.46.0 there.
            if stripped.startswith("/*") or stripped.startswith("{/*"):
                yield number, line
                if "*/" not in stripped.split("/*", 1)[1]:
                    open_block = True
                continue
            cleaned = _strip_strings(line)
            if "//" in cleaned and "://" not in cleaned:
                yield number, cleaned.split("//", 1)[1]
        elif suffix == ".yml":
            if stripped.startswith("#"):
                yield number, line
            # A workflow's own prose: what an input means and what it prints
            # when it refuses. Read by whoever runs the workflow from the
            # Actions tab, so it is interface rather than data.
            elif stripped.startswith("description:") or "::error::" in line \
                    or "::warning::" in line or stripped.startswith("echo "):
                yield number, line


def source_files() -> list[Path]:
    found: list[Path] = []
    for folder, patterns in SOURCES:
        for pattern in patterns:
            for path in sorted((ROOT / folder).rglob(pattern)):
                if "__pycache__" in str(path) or "node_modules" in str(path):
                    continue
                # This file quotes Dutch to prove the word list works; scanning
                # itself would make it fail on its own examples.
                if path.name == Path(__file__).name:
                    continue
                found.append(path)
    return found


@pytest.mark.parametrize("folder", [folder for folder, _ in SOURCES])
def test_the_comments_in_this_folder_are_english(folder: str):
    """A Dutch comment names the file and the line, so it can be fixed at once."""
    offenders: list[str] = []
    for path in source_files():
        if not str(path).startswith(str(ROOT / folder)):
            continue
        for number, prose in comment_lines(path):
            if DUTCH.search(prose):
                offenders.append(f"{path.relative_to(ROOT)}:{number}: {prose.strip()[:90]}")

    assert offenders == [], (
        "Dutch comments found. The interface speaks four languages, the source speaks "
        "one — see docs/development.md.\n" + "\n".join(offenders[:20])
    )


def test_the_guard_actually_reads_something():
    """A word list that matches nothing would pass on an empty scan just as well."""
    files = source_files()
    assert len(files) > 100
    total = sum(1 for path in files for _ in comment_lines(path))
    assert total > 2000, f"only {total} comment lines seen; the scanner is missing files"


def test_the_word_list_recognises_dutch_when_it_sees_it():
    """The other direction: proof the guard would fire.

    Kept because a regex that is quietly broken — an unescaped group, a stray
    flag — turns this whole file into a test that always passes.
    """
    assert DUTCH.search("# Dit wordt niet vertaald")
    assert DUTCH.search("    Een regel die uitlegt waarom.")
    assert not DUTCH.search("# The class column only says '2' for gases")
    assert not DUTCH.search("    Rounded up to one decimal, over the unrounded sum.")
