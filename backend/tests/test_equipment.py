import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.models.user import Equipment
from app.services.pipeline import match_equipment, parse_and_calculate


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


def _seed_skoda(db: Session) -> None:
    db.add(
        Equipment(
            sap_code="SKODA YETI",
            specifications="VEHICLE SKODA YETI",
            length_cm=402,
            width_cm=179,
            height_cm=169,
            weight_kg=1370,
            aliases_json=json.dumps(["skoda yeti", "vehicle skoda yeti"]),
            language_labels_json=json.dumps({"nl": "SKODA YETI"}),
            source="overzicht_materieel",
            active=True,
        )
    )
    db.commit()


def test_match_equipment_skoda_yeti(db: Session):
    _seed_skoda(db)
    item = match_equipment("Skoda Yeti | 1 | stuks", db)
    assert item is not None
    assert item.sap_code == "SKODA YETI"
    assert item.weight_kg == 1370


def test_parse_skoda_yeti_line(db: Session):
    _seed_skoda(db)
    result = parse_and_calculate("skoda yeti | 1 | stuk", db)
    assert result["success"]
    line = result["lines"][0]
    assert line["product_type"] == "equipment"
    assert line["weight_each_kg"] == 1370
    assert line["weight_total_kg"] == 1370
    assert line["output_description"] == "VEHICLE SKODA YETI"
    assert line["length_cm"] == 402


def test_weight_override_on_recalculate(db: Session):
    _seed_skoda(db)
    result = parse_and_calculate(
        "skoda yeti | 2 | stuks",
        db,
        line_overrides=[{"line_id": 1, "weight_each_kg": 1000}],
    )
    assert result["success"]
    line = result["lines"][0]
    assert line["weight_each_kg"] == 1000
    assert line["weight_total_kg"] == 2000
