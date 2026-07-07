import json

import pytest
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.models.user import Equipment
from app.services.pipeline import match_equipment, parse_and_calculate


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


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
