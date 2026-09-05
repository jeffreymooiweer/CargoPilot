"""Box 24 of the CIM gets a list to pick from.

The seed is the UIC's own NST 2007 – NHM 2025 correspondence table, cut to
one entry per six-digit code by scripts/build_nhm_seed.py. What is pinned
here: the seed's shape and size, the two ways of searching it, the one
code the table only knew in eight-digit pieces, the railway-specific
positions, and the endpoint behind the login.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.services.nhm import nhm_count, nhm_entry, search_nhm

SEED = Path(__file__).resolve().parents[1] / "seed" / "nhm.json"


def test_the_seed_is_one_entry_per_six_digit_code_with_both_labels():
    entries = json.loads(SEED.read_text(encoding="utf-8"))
    codes = [e["code"] for e in entries]
    assert len(codes) == len(set(codes)) == 5640
    assert all(len(c) == 6 and c.isdigit() for c in codes)
    assert all(e["en"] and e["fr"] and e["nst"] for e in entries)
    assert codes == sorted(codes)


def test_the_railway_positions_of_chapter_99_are_in():
    rail = [e for e in json.loads(SEED.read_text(encoding="utf-8")) if e["code"].startswith("99")]
    assert len(rail) == 28
    assert nhm_entry("990200")["en"] == "Groupage freight"


def test_the_one_code_the_table_only_knew_in_pieces_has_its_heading_label():
    assert nhm_entry("070200")["en"] == "Tomatoes, fresh or chilled"


def test_a_code_prefix_lists_the_subheadings_under_it():
    hits = search_nhm("7208")
    assert hits and all(h["code"].startswith("7208") for h in hits)
    assert "720851" in {h["code"] for h in search_nhm("7208 5")}
    assert search_nhm("720851")[0]["en"].startswith("Flat-rolled products of iron or non-alloy steel")


def test_a_word_finds_the_label_in_either_language():
    hits = search_nhm("flat-rolled", limit=25)
    assert hits and all("flat-rolled" in h["en"].lower() for h in hits)
    assert any(h["code"].startswith("27") for h in search_nhm("pétrole", limit=25))
    # Accents do not decide: the French label is found without them too.
    assert search_nhm("petrole", limit=25) == search_nhm("pétrole", limit=25)


def test_a_word_start_outranks_a_word_middle_and_shorter_outranks_longer():
    hits = search_nhm("tomato")
    assert hits[0]["code"] == "070200"


def test_nothing_is_answered_for_nothing():
    assert search_nhm("") == []
    assert search_nhm("x") == []
    assert nhm_entry("000000") is None
    assert nhm_count() == 5640


def _client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="test", role="user", active=True)
    return TestClient(app)


def test_the_endpoint_searches_and_looks_up():
    try:
        client = _client()
        response = client.get("/api/nhm", params={"q": "7208 51"})
        assert response.status_code == 200
        assert response.json()["results"][0]["code"] == "720851"
        assert response.json()["count"] == 5640
        assert client.get("/api/nhm/720851").json()["fr"].startswith("Produits laminés plats")
        assert client.get("/api/nhm/123456").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_the_endpoint_is_behind_the_login():
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/nhm", params={"q": "7208"}).status_code == 401
