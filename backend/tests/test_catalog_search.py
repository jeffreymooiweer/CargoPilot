import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.core.startup import seed_catalogs
from app.services.catalog_search import normalize_synonyms, search_catalog


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()

    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    session = sessionmaker(bind=test_engine)()
    seed_catalogs(session)
    yield session
    session.close()
    get_settings.cache_clear()


def test_normalize_hoeklijn_to_hoekprofiel():
    normalized, applied = normalize_synonyms("staal hoeklijn")
    assert "hoekprofiel" in normalized
    assert ("hoeklijn", "hoekprofiel") in applied


def test_search_staal_hoeklijn_suggests_hoekprofiel(db):
    results = search_catalog(db, "staal hoeklijn")
    assert results
    top = results[0]
    assert "hoekprofiel" in top["value"].lower()
    assert "staal" in top["value"].lower()
    assert top["source"] == "template"


def test_search_staal_hoeklijn_with_dimensions(db):
    results = search_catalog(db, "staal hoeklijn 80x80x8x6000")
    assert results
    value = results[0]["value"].lower()
    assert "hoekprofiel" in value
    assert "80x80x8x6000" in value.replace(" ", "")


def test_search_finds_equipment(db):
    results = search_catalog(db, "skoda yeti")
    assert any("skoda" in r["value"].lower() for r in results)
    assert any(r["source"] == "equipment" for r in results)


def test_search_finds_steel_profile(db):
    results = search_catalog(db, "UNP 220")
    assert any(r["source"] == "profile" for r in results)
    assert any("220" in r["label"] for r in results)


def test_search_short_query_returns_empty(db):
    assert search_catalog(db, "s") == []
