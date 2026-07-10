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


def _seed_demo_vehicle(db: Session) -> None:
    db.add(
        Equipment(
            sap_code="DEMO-001",
            specifications="VEHICLE DEMO-001",
            length_cm=402,
            width_cm=179,
            height_cm=169,
            weight_kg=1370,
            aliases_json=json.dumps(["demo vehicle", "vehicle demo vehicle"]),
            language_labels_json=json.dumps({"nl": "DEMO-001"}),
            source="overzicht_materieel",
            active=True,
        )
    )
    db.commit()


def test_match_equipment_demo_vehicle(db: Session):
    _seed_demo_vehicle(db)
    item = match_equipment("Demo vehicle | 1 | stuks", db)
    assert item is not None
    assert item.sap_code == "DEMO-001"
    assert item.weight_kg == 1370


def test_parse_demo_vehicle_line(db: Session):
    _seed_demo_vehicle(db)
    result = parse_and_calculate("demo vehicle | 1 | stuk", db)
    assert result["success"]
    line = result["lines"][0]
    assert line["product_type"] == "equipment"
    assert line["weight_each_kg"] == 1370
    assert line["weight_total_kg"] == 1370
    assert line["output_description"] == "VEHICLE DEMO-001"
    assert line["length_cm"] == 402


def test_weight_override_on_recalculate(db: Session):
    _seed_demo_vehicle(db)
    result = parse_and_calculate(
        "demo vehicle | 2 | stuks",
        db,
        line_overrides=[{"line_id": 1, "weight_each_kg": 1000}],
    )
    assert result["success"]
    line = result["lines"][0]
    assert line["weight_each_kg"] == 1000
    assert line["weight_total_kg"] == 2000
