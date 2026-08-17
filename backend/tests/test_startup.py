
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.core.startup import migrate_equipment_columns, purge_legacy_equipment
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
    assert remaining[0].specifications == "USER ITEM"


def test_an_older_equipment_table_is_brought_in_line(tmp_path, monkeypatch):
    """A library filled before v1.116.0 has a SAP code column and no wall
    thickness. ``create_all`` never touches the columns of a table that
    already exists, so the equipment page would fail on the very first query
    until this migration runs — and it must be safe to run on every start.
    """
    from sqlalchemy import inspect, text

    db_path = tmp_path / "old.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        connection.execute(text(
            """
            CREATE TABLE equipment_items (
                id INTEGER PRIMARY KEY,
                sap_code VARCHAR(128),
                specifications VARCHAR(255),
                length_cm FLOAT, width_cm FLOAT, height_cm FLOAT,
                weight_kg FLOAT, aliases_json TEXT, language_labels_json TEXT,
                source VARCHAR(64), notes TEXT, active BOOLEAN
            )
            """
        ))
        connection.execute(text(
            "INSERT INTO equipment_items (sap_code, specifications, weight_kg, "
            "aliases_json, language_labels_json, source, active) "
            "VALUES ('OLD-1', 'OLD ITEM', 100, '[]', '{}', 'import', 1)"
        ))
    session = sessionmaker(bind=engine)()
    try:
        migrate_equipment_columns(session)
        columns = {c["name"] for c in inspect(engine).get_columns("equipment_items")}
        assert "wall_thickness_mm" in columns
        assert "sap_code" not in columns
        # The items themselves survive, and are readable through the model.
        item = session.query(Equipment).one()
        assert item.specifications == "OLD ITEM"
        assert item.wall_thickness_mm is None
        # Running it again changes nothing and raises nothing.
        migrate_equipment_columns(session)
        assert session.query(Equipment).count() == 1
    finally:
        session.close()
        get_settings.cache_clear()
