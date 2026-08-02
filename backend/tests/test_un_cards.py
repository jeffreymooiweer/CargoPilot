"""Tests for handing the user the UN cards for their own substances.

The point of the feature is selectivity: a shipment of gasoline should get the
gasoline card and nothing else. It also has to stay out of the way when the card
library is absent, which is the state of any fork that has not run the fetch
workflow — including this test suite's default.
"""

import zipfile

import pytest

from app.services.documents import un_cards


@pytest.fixture
def library(tmp_path, monkeypatch):
    """A small stand-in card library."""
    for name in ("un_1203.pdf", "un_1203-2.pdf", "un_1017.pdf", "un_2031.pdf"):
        (tmp_path / name).write_bytes(b"%PDF-1.4\n% card " + name.encode() + b"\n%%EOF\n")
    # Files that are not cards must be ignored, not shipped to the user.
    (tmp_path / "manifest.json").write_text('{"summary": {"identified": 3}}')
    (tmp_path / "notes.txt").write_text("scratch")
    monkeypatch.setenv("UN_CARDS_DIR", str(tmp_path))
    un_cards.reset_cache()
    yield tmp_path
    un_cards.reset_cache()


@pytest.fixture
def no_library(tmp_path, monkeypatch):
    monkeypatch.setenv("UN_CARDS_DIR", str(tmp_path / "absent"))
    un_cards.reset_cache()
    yield
    un_cards.reset_cache()


def dg(*un_numbers):
    return [{"line_id": 1, "products": [{"un_number": un} for un in un_numbers]}]


def test_only_the_declared_substances_are_bundled(library):
    path, status = un_cards.build_zip(dg("1203"))
    try:
        names = zipfile.ZipFile(path).namelist()
    finally:
        path.unlink(missing_ok=True)

    assert status["available"] == ["1203"]
    # Both cards for UN 1203, and nothing about chlorine or nitric acid.
    assert sorted(n for n in names if n.endswith(".pdf")) == ["un_1203-2.pdf", "un_1203.pdf"]
    assert "un_1017.pdf" not in names


def test_the_zip_explains_itself(library):
    path, _status = un_cards.build_zip(dg("1203", "9999"))
    try:
        readme = zipfile.ZipFile(path).read("README.txt").decode()
    finally:
        path.unlink(missing_ok=True)

    assert "UN 1203" in readme
    # A substance we hold no card for is stated, not quietly dropped.
    assert "No card is held" in readme and "UN 9999" in readme
    assert "do not replace the current edition" in readme


def test_un_numbers_are_read_from_the_declared_products(library):
    entries = [
        {"line_id": 1, "products": [{"un_number": "UN 1203"}, {"un_number": "1017"}]},
        {"line_id": 2, "products": [{"un_number": "1203"}]},  # duplicate
        {"line_id": 3, "products": [{"un_number": ""}]},
    ]
    assert un_cards.un_numbers_in(entries) == ["1203", "1017"]


def test_availability_separates_what_we_have_from_what_we_do_not(library):
    status = un_cards.availability(dg("1203", "9999", "1017"))
    assert status["enabled"] is True
    assert status["available"] == ["1203", "1017"]
    assert status["missing"] == ["9999"]
    assert status["count"] == 2


def test_non_card_files_are_not_part_of_the_library(library):
    assert un_cards.card_count() == 3  # 1203, 1017, 2031 — not manifest.json or notes.txt


def test_without_a_library_the_feature_reports_itself_unavailable(no_library):
    assert un_cards.has_un_cards() is False
    status = un_cards.availability(dg("1203"))
    assert status == {
        "enabled": False, "requested": ["1203"], "available": [], "missing": ["1203"], "count": 0,
    }
    with pytest.raises(FileNotFoundError):
        un_cards.build_zip(dg("1203"))


def test_a_shipment_without_dangerous_goods_asks_for_nothing(library):
    assert un_cards.availability(None)["available"] == []
    with pytest.raises(FileNotFoundError):
        un_cards.build_zip(None)
