import pytest
from app.core.database import Base, SessionLocal, engine
from app.core.startup import seed_catalogs
from app.services.catalog_sync import sync_catalogs
from app.models.user import Material, Profile


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_catalogs(session)
    yield session
    session.close()


def test_sync_imports_steel_profiles(db):
    status = sync_catalogs(db, use_network=False)
    assert status["profile_count"] >= 400
    unp220 = (
        db.query(Profile)
        .filter(Profile.size_label == "220", Profile.profile_type.in_(["UPN", "UNP"]))
        .first()
    )
    assert unp220 is not None
    assert abs(unp220.kg_per_meter - 29.4) < 0.1
    assert unp220.source and "steelprofiles" in unp220.source


def test_sync_imports_hollow_profiles(db):
    sync_catalogs(db, use_network=False)
    shs = db.query(Profile).filter(Profile.profile_type == "SHS").first()
    rhs = db.query(Profile).filter(Profile.profile_type == "RHS").first()
    chs = db.query(Profile).filter(Profile.profile_type == "CHS").first()
    assert shs is not None and shs.kg_per_meter > 0
    assert rhs is not None and rhs.kg_per_meter > 0
    assert chs is not None and chs.kg_per_meter > 0
    assert "eurocodepy" in (shs.source or "")


def test_sync_updates_material_densities(db):
    status = sync_catalogs(db, use_network=False)
    assert status["material_count"] >= 15
    steel = db.query(Material).filter(Material.canonical_name == "steel").first()
    assert steel is not None
    assert steel.density_kg_m3 == 7850
    brick = db.query(Material).filter(Material.canonical_name == "brick").first()
    assert brick is not None


def test_sync_status_persisted(db, tmp_path, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    sync_catalogs(db, use_network=False)
    status_file = tmp_path / "catalog_sync_status.json"
    assert status_file.exists()
