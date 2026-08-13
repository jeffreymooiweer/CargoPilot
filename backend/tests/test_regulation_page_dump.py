"""A table is not text, and the finder looks for text.

``locate`` chooses between all the places an article number occurs by counting
how many letters follow it. For a provision made of sentences that is the right
rule. For ADR 7.5.2.1 it is the wrong one: that article is almost entirely a grid
of crosses with a number in the margin, so it scores nearly zero and loses to
every cross-reference elsewhere in the volume. The finder reported "not found"
while the provision is simply there.

Hence ``--page``: if the number cannot be found, the page can. What is recorded
here is mainly what must *not* happen — putting a range of a thousand pages into
a run log, or treating a reversed range silently as empty.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "read_land_regulations", ROOT / "scripts" / "read_land_regulations.py"
)
reader = importlib.util.module_from_spec(SPEC)
# @dataclass looks its own module up in sys.modules; registering after the
# exec is too late and fails with an AttributeError that says nothing.
sys.modules[SPEC.name] = reader
SPEC.loader.exec_module(reader)


def test_a_single_page_is_a_range_of_one():
    assert reader.parse_pages("594") == [594]


def test_a_range_runs_inclusive():
    """600-606 is seven pages, not six: whoever asks for a chapter wants its last
    page as well."""
    assert reader.parse_pages("600-606") == [600, 601, 602, 603, 604, 605, 606]


def test_surrounding_space_does_not_matter():
    assert reader.parse_pages("  594 ") == [594]


@pytest.mark.parametrize("spec", ["606-600", "0", "-3", "0-4"])
def test_a_range_that_makes_no_sense_is_refused(spec):
    with pytest.raises(ValueError):
        reader.parse_pages(spec)


def test_a_range_wider_than_a_chapter_is_refused():
    """The brake. Without this limit one typo puts the whole volume in the run
    log and there is nothing left to read back."""
    with pytest.raises(ValueError):
        reader.parse_pages("1-13")


def test_twelve_pages_is_still_allowed():
    assert len(reader.parse_pages("100-111")) == 12


@pytest.mark.parametrize("spec", ["banana", "", "1-", "1-2-3"])
def test_something_that_is_not_a_page_is_refused(spec):
    with pytest.raises(ValueError):
        reader.parse_pages(spec)


# --- Searching through a hyphenation --------------------------------------
#
# RID hyphenates words at the end of a line. A search for "alkaline earth metal
# nitrates" therefore returned "no occurrence", and that read as a statement
# about the regulations while it was a statement about the typesetting. For a
# reading tool that is the worst imaginable fault.


def test_a_word_broken_at_the_line_end_is_still_found():
    text = "articles of com-\npatibility group D may be loaded"
    haystack, _ = reader._searchable(text)
    needle, _ = reader._searchable("compatibility group D")
    assert needle in haystack


def test_the_position_points_back_into_the_real_text():
    """The fragment that gets printed has to be the real fragment, hyphen and
    all — otherwise you quote something that is not there."""
    text = "zie divi-\nsion 1.1 hierna"
    haystack, origin = reader._searchable(text)
    needle, _ = reader._searchable("division")
    start = origin[haystack.index(needle)]
    assert text[start:].startswith("divi-")


def test_case_and_stray_spacing_do_not_matter():
    haystack, _ = reader._searchable("ALKALI   metal\n  NITRATES")
    needle, _ = reader._searchable("alkali metal nitrates")
    assert needle in haystack


def test_a_genuine_hyphen_is_dropped_on_both_sides():
    """"self-reactive" becomes "selfreactive", and so does the search term. As
    long as both sides get the same treatment, the search term keeps working."""
    haystack, _ = reader._searchable("self-reactive substances")
    needle, _ = reader._searchable("self-reactive")
    assert needle in haystack


def test_a_hyphen_between_words_does_not_glue_a_sentence_together():
    """The hyphen disappears, but an em dash must not glue together two words
    that stand apart in the text."""
    haystack, _ = reader._searchable("klasse 5.1 - zie hierna")
    assert "5.1 zie hierna" in haystack


# --- A table is not a table of contents ------------------------------------
#
# The third table-of-contents signal counted bare numbers, and thereby skipped
# exactly the wrong pages. Table 7.5.2.1 is a column of "1.4", "5.1", "6.2" —
# dozens of bare numbers and not a table of contents in sight. RID's 7.5.2.1 was
# skipped because of it and the finder reported "no occurrence" about a footnote
# that is simply there, on page 1101.

TABLE_PAGE = (
    "\n".join(["1", "1.4", "1.5", "1.6", "2.1", "2.2", "2.3", "3", "4.1", "4.2",
               "4.3", "5.1", "5.2", "6.1", "6.2", "7.1", "8.1", "9.1", "9.2"])
    + "\n"
    + "\n".join([
        "Packages bearing different danger labels shall not be loaded together in one wagon.",
        "NOTE 1: separate transport documents shall be drawn up for such consignments.",
        "(a) Mixed loading permitted with 1.4S substances and articles, without further condition.",
        "(b) Mixed loading permitted between goods of Class 1 and life-saving appliances of Class 9.",
        "(d) Mixed loading permitted between blasting explosives and ammonium nitrate, provided that.",
    ])
)

CONTENTS_PAGE = "\n".join(["7.5.1", "7.5.2", "7.5.2.1", "7.5.2.2", "7.5.2.3", "7.5.2.4",
                           "7.5.3", "7.5.4", "7.5.5", "7.5.5.1", "7.5.5.2", "7.5.5.3",
                           "7.5.6", "7.5.7", "7.5.8", "7.5.9", "7.5.10", "7.5.11",
                           "7.6", "7.7"])


def test_a_table_full_of_numbers_is_not_a_contents_page():
    assert reader._is_contents_page(TABLE_PAGE) is False


def test_a_real_contents_page_is_still_recognised():
    assert reader._is_contents_page(CONTENTS_PAGE) is True


def test_dot_leaders_still_count_on_their_own():
    """That signal is specific enough; counting numbers alone was not."""
    page = "\n".join([f"1.{n} Something ......... {n}" for n in range(1, 6)])
    assert reader._is_contents_page(page) is True


def test_the_chapter_page_column_still_counts_on_its_own():
    assert reader._is_contents_page("\n".join(["1-3", "2-4", "3-5", "4-6", "5-7"])) is True


def test_the_finder_actually_uses_it():
    source = (ROOT / "scripts" / "read_land_regulations.py").read_text(encoding="utf-8")
    finder = source[source.index("def find("):]
    assert "_searchable" in finder[: finder.index("\ndef ")]


def test_the_dump_is_reachable_from_the_command_line():
    """The option only really exists once main passes it on; a function without a
    flag is exactly the kind of seam this went wrong on before."""
    source = (ROOT / "scripts" / "read_land_regulations.py").read_text(encoding="utf-8")
    assert '"--page"' in source
    assert "dump(doc, number)" in source


def test_the_workflow_offers_it_too():
    workflow = (ROOT / ".github" / "workflows" / "read-land-regulations.yml").read_text(
        encoding="utf-8"
    )
    assert "--page" in workflow


# --- "later" is not "no" ----------------------------------------------------
#
# The Archive answers 503 when it is busy, and busy is its normal state. The ADN
# URL that served 19 MB at 05:11 served 503 at 13:48 and again at 15:56, and
# each of those cost a whole workflow run to find out. What is checked here is
# that a temporary status is asked again and a permanent one is not — waiting
# out a 404 would be just as wasteful in the other direction.


class _Answers:
    """Stands in for curl: hands out a prepared reply per call and counts them."""

    def __init__(self, replies, pdf_on=None):
        self.replies = list(replies)
        self.pdf_on = pdf_on
        self.calls = 0

    def __call__(self, url, target, extra=None):
        code = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        if self.pdf_on is not None and self.calls >= self.pdf_on:
            target.write_bytes(b"%PDF-1.7\n")
        return code, "application/pdf" if code == 200 else "text/html"


@pytest.fixture
def no_waiting(monkeypatch):
    """The waits are real seconds; the test is about the decisions, not the clock."""
    monkeypatch.setattr(reader.time, "sleep", lambda _s: None)


def test_a_busy_archive_is_asked_again(monkeypatch, no_waiting, tmp_path):
    answers = _Answers([503, 503, 200], pdf_on=3)
    monkeypatch.setattr(reader, "_curl", answers)
    code, _kind = reader._ask("https://example.invalid/x.pdf", tmp_path / "x.pdf", [], "web archive")
    assert code == 200
    assert answers.calls == 3


def test_a_missing_file_is_not_asked_again(monkeypatch, no_waiting, tmp_path):
    """404 means the address moved. Asking four times still gets a 404, and the
    run needs to reach the message that says to check the download page."""
    answers = _Answers([404])
    monkeypatch.setattr(reader, "_curl", answers)
    code, _kind = reader._ask("https://example.invalid/x.pdf", tmp_path / "x.pdf", [], "direct")
    assert code == 404
    assert answers.calls == 1


def test_it_gives_up_rather_than_asking_forever(monkeypatch, no_waiting, tmp_path):
    answers = _Answers([503])
    monkeypatch.setattr(reader, "_curl", answers)
    reader._ask("https://example.invalid/x.pdf", tmp_path / "x.pdf", [], "web archive")
    assert answers.calls == len(reader.RETRY_WAITS) + 1


def test_the_half_written_error_page_is_cleared_between_asks(monkeypatch, no_waiting, tmp_path):
    """curl writes the 503 page to the target. Left in place, the next ask would
    append to it and the PDF check would look at a file that is part error."""
    target = tmp_path / "x.pdf"

    def curl(url, dest, extra=None):
        if not dest.exists():
            dest.write_bytes(b"<html>busy</html>")
            return 503, "text/html"
        curl.left_behind = True
        return 503, "text/html"

    curl.left_behind = False
    monkeypatch.setattr(reader, "_curl", curl)
    reader._ask("https://example.invalid/x.pdf", target, [], "web archive")
    assert curl.left_behind is False
