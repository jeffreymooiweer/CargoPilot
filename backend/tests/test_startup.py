import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.core.startup import purge_legacy_equipment
from app.models.user import Equipment


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
    yield session
    session.close()
    get_settings.cache_clear()


def test_purge_legacy_equipment(db):
    db.add(
        Equipment(
            sap_code="LEGACY-1",
            specifications="LEGACY ITEM",
            weight_kg=100,
            aliases_json="[]",
            language_labels_json="{}",
            source="overzicht_materieel",
            active=True,
        )
    )
    db.add(
        Equipment(
            sap_code="USER-1",
            specifications="USER ITEM",
            weight_kg=200,
            aliases_json="[]",
            language_labels_json="{}",
            source="import",
            active=True,
        )
    )
    db.commit()
    purge_legacy_equipment(db)
    remaining = db.query(Equipment).all()
    assert len(remaining) == 1
    assert remaining[0].sap_code == "USER-1"
