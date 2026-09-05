"""The shipment history: kept only where the switch is on, and never orphaned.

What is pinned here, in the order it matters:

1. **Without the switch the addresses do not exist.** Not 401, not 403 — 404,
   like every other route the installation does not have. The open
   application ignores the switch altogether.
2. **Switching the history off with shipments in the table refuses to
   start**, names the count and the discard variable, and deletes nothing.
   With the discard variable set it deletes them and says so.
3. **The kept record is the structured export, built by the server** from
   the same parts the download uses, so the two cannot disagree — and the
   index columns a list filters on come out of it.
4. **The documents again come from the kept bundle**, through the same code
   path as the export step's download.
5. **The schema runner** stamps a fresh database and migrates an old one, and
   running it twice does nothing the second time.
"""
from __future__ import annotations

import io
import logging
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core import migrations
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import create_app
from app.models.shipment import Shipment
from app.models.user import User
from app.services import history, settings_store
from tests.test_export_bundle import CONSIGNMENT, DG, doc


#: The real schema steps, so adding one does not renumber every assertion.
STEPS = [version for version, _name, _step in migrations.MIGRATIONS]
NEXT = STEPS[-1] + 1


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{data_dir / 'test.db'}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CATALOG_AUTO_SYNC", "false")
    monkeypatch.delenv("CARGOPILOT_HISTORY", raising=False)
    monkeypatch.delenv("CARGOPILOT_HISTORY_DISCARD", raising=False)
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{data_dir / 'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, username="ada", email="ada@example.com",
                     password_hash="x", role="user"))
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


def application(db, monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, 1)
    return TestClient(app)


ADA = SimpleNamespace(id=1, username="ada", role="user", active=True)


def shipment(**overrides) -> dict:
    payload = {
        "modality": "road",
        "language": "nl",
        "profiles": ["ADR"],
        "values": dict(CONSIGNMENT),
        "lines": [{"description": "Vaten benzine", "quantity": 4, "weight_total_kg": 800.0}],
        "dangerous_goods": DG,
        "documents": ["cmr"],
        "bundle": {"documents": [doc("cmr")], "dangerous_goods": DG,
                   "profiles": ["ADR"], "output_language": "nl"},
        "snapshot": {"version": 1, "stepKey": "export", "docValues": dict(CONSIGNMENT)},
    }
    payload.update(overrides)
    return payload


# --- 1. the addresses exist only with the switch --------------------------------


def test_without_the_switch_the_shipments_routes_do_not_exist(db, monkeypatch):
    with application(db, monkeypatch) as client:
        assert client.get("/api/shipments").status_code == 404
        assert client.post("/api/shipments", json=shipment()).status_code == 404
        assert client.get("/api/settings/public").json()["history_enabled"] is False
        assert client.get("/api/health").json()["history"] is False


def test_with_the_switch_they_do(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true") as client:
        assert client.get("/api/shipments").status_code == 200
        assert client.get("/api/settings/public").json()["history_enabled"] is True
        assert client.get("/api/health").json()["history"] is True


def test_the_open_application_ignores_the_switch(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true",
                     CARGOPILOT_MODE="open") as client:
        assert client.get("/api/shipments").status_code == 404
        assert client.get("/api/health").json()["history"] is False
    assert get_settings().history_enabled is False


# --- 2. switching off refuses to start --------------------------------------------


def test_shipments_left_behind_refuse_to_start_and_are_not_deleted(db, monkeypatch, caplog):
    monkeypatch.setenv("CARGOPILOT_HISTORY", "true")
    get_settings.cache_clear()
    history.keep(db, ADA, history.ShipmentIn(**shipment()))
    history.keep(db, ADA, history.ShipmentIn(**shipment()))

    monkeypatch.setenv("CARGOPILOT_HISTORY", "false")
    get_settings.cache_clear()
    with pytest.raises(SystemExit) as refused:
        history.enforce_switch(db)
    message = str(refused.value)
    assert "2 kept shipment(s)" in message
    assert "CARGOPILOT_HISTORY_DISCARD" in message
    assert history.count(db) == 2


def test_the_discard_variable_deletes_them_and_says_so(db, monkeypatch, caplog):
    monkeypatch.setenv("CARGOPILOT_HISTORY", "true")
    get_settings.cache_clear()
    history.keep(db, ADA, history.ShipmentIn(**shipment()))

    monkeypatch.setenv("CARGOPILOT_HISTORY", "false")
    monkeypatch.setenv("CARGOPILOT_HISTORY_DISCARD", "true")
    get_settings.cache_clear()
    with caplog.at_level(logging.WARNING):
        history.enforce_switch(db)
    assert history.count(db) == 0
    assert "discarded 1 kept shipment(s)" in caplog.text


def test_with_the_switch_on_nothing_is_touched(db, monkeypatch):
    monkeypatch.setenv("CARGOPILOT_HISTORY", "true")
    get_settings.cache_clear()
    history.keep(db, ADA, history.ShipmentIn(**shipment()))
    history.enforce_switch(db)
    assert history.count(db) == 1


def test_an_empty_table_never_refuses(db):
    history.enforce_switch(db)


# --- 3. the kept record ---------------------------------------------------------


def test_keeping_builds_the_export_and_the_index_from_the_same_parts(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true") as client:
        created = client.post("/api/shipments", json=shipment())
        assert created.status_code == 200, created.text
        summary = created.json()
        assert summary["reference"] == "CP-2026-100"
        assert summary["consignor_name"] == "Afzender BV"
        # The wizard's own field name wins over the fallback.
        wizard_named = client.post("/api/shipments", json=shipment(
            values={**CONSIGNMENT, "shipment_reference": "WZ-1"})).json()
        assert wizard_named["reference"] == "WZ-1"
        assert summary["consignee_name"] == "Ontvanger GmbH"
        assert summary["modality"] == "road"
        assert summary["regulations"] == ["ADR"]
        assert summary["goods_count"] == 1
        assert summary["has_dangerous_goods"] is True
        assert summary["has_documents"] is True
        assert summary["created_by"] == "ada"

        detail = client.get(f"/api/shipments/{summary['id']}").json()
        export = detail["export"]
        assert export["format"] == "cargopilot.shipment"
        assert export["consignment"]["reference"] == "CP-2026-100"
        assert export["regulations"] == ["ADR"]
        # The derived half is there, with the editions it was computed against.
        assert "compliance" in export
        assert detail["snapshot"]["stepKey"] == "export"

        as_file = client.get(f"/api/shipments/{summary['id']}/export.json")
        assert as_file.status_code == 200
        assert 'filename="cargopilot-shipment-CP-2026-100.json"' in \
            as_file.headers["content-disposition"]


def test_keeping_again_brings_the_same_row_up_to_date(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true") as client:
        first = client.post("/api/shipments", json=shipment()).json()
        changed = shipment(values={**CONSIGNMENT, "reference": "CP-2026-101"})
        second = client.put(f"/api/shipments/{first['id']}", json=changed).json()
        assert second["id"] == first["id"]
        assert second["reference"] == "CP-2026-101"
        assert client.get("/api/shipments").json()["total"] == 1


def test_the_list_filters_and_pages_newest_first(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true") as client:
        for reference, modality in (("A-1", "road"), ("B-2", "sea"), ("A-3", "road")):
            client.post("/api/shipments", json=shipment(
                modality=modality, values={**CONSIGNMENT, "reference": reference}))
        everything = client.get("/api/shipments").json()
        assert [s["reference"] for s in everything["items"]] == ["A-3", "B-2", "A-1"]
        assert everything["total"] == 3

        assert [s["reference"] for s in
                client.get("/api/shipments?q=a-").json()["items"]] == ["A-3", "A-1"]
        assert [s["reference"] for s in
                client.get("/api/shipments?modality=sea").json()["items"]] == ["B-2"]
        by_name = client.get("/api/shipments?q=ontvanger").json()
        assert by_name["total"] == 3

        page = client.get("/api/shipments?per_page=2&page=2").json()
        assert [s["reference"] for s in page["items"]] == ["A-1"]
        assert page["total"] == 3


def test_a_shipment_kept_without_ready_documents_says_so(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true") as client:
        kept = client.post("/api/shipments", json=shipment(bundle=None)).json()
        assert kept["has_documents"] is False
        again = client.post(f"/api/shipments/{kept['id']}/documents")
        assert again.status_code == 404


def test_forgetting_removes_the_row(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true") as client:
        kept = client.post("/api/shipments", json=shipment()).json()
        assert client.delete(f"/api/shipments/{kept['id']}").json()["ok"] is True
        assert client.get(f"/api/shipments/{kept['id']}").status_code == 404
        assert client.delete(f"/api/shipments/{kept['id']}").status_code == 404
    assert history.count(db) == 0


def test_a_record_too_large_is_refused_before_it_is_kept(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true") as client:
        bloated = shipment(snapshot={"blob": "x" * (history.MAX_RECORD_BYTES + 1)})
        assert client.post("/api/shipments", json=bloated).status_code == 413
    assert history.count(db) == 0


# --- 4. the documents again -----------------------------------------------------


def test_the_documents_again_are_the_kept_bundle_rerendered(db, monkeypatch):
    with application(db, monkeypatch, CARGOPILOT_HISTORY="true") as client:
        kept = client.post("/api/shipments", json=shipment()).json()
        again = client.post(f"/api/shipments/{kept['id']}/documents")
        assert again.status_code == 200, again.text
        assert again.headers["content-type"] == "application/zip"
        assert "CP-2026-100" in again.headers["content-disposition"]
        with zipfile.ZipFile(io.BytesIO(again.content)) as archive:
            names = archive.namelist()
        assert any(name.lower().startswith("cmr") or "cmr" in name.lower() for name in names), names


# --- 5. the schema runner -------------------------------------------------------


def test_a_fresh_database_is_stamped_and_an_old_one_migrated(tmp_path):
    fresh_engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    Base.metadata.create_all(bind=fresh_engine)
    assert migrations.run(fresh_engine, fresh=True) == STEPS
    assert migrations.current(fresh_engine) == STEPS[-1]
    assert inspect(fresh_engine).has_table("shipments")

    # A database from before v1.173.0: the users table exists, shipments does not.
    old_engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    User.__table__.create(old_engine)
    assert not inspect(old_engine).has_table("shipments")
    assert migrations.run(old_engine, fresh=False) == STEPS
    assert inspect(old_engine).has_table("shipments")
    # Twice does nothing the second time.
    assert migrations.run(old_engine, fresh=False) == []
    assert migrations.current(old_engine) == STEPS[-1]


def test_a_later_step_runs_on_an_old_database_and_is_stamped_on_a_fresh_one(tmp_path, monkeypatch):
    ran: list[str] = []

    def _004_colour(conn):
        ran.append(f"{NEXT:03d}")
        migrations.add_column(conn, "shipments", "colour VARCHAR(16)")

    monkeypatch.setattr(migrations, "MIGRATIONS",
                        migrations.MIGRATIONS + [(NEXT, "colour", _004_colour)])

    old_engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    User.__table__.create(old_engine)
    assert migrations.run(old_engine, fresh=False) == STEPS + [NEXT]
    assert ran == [f"{NEXT:03d}"]
    with old_engine.connect() as conn:
        assert migrations.column_exists(conn, "shipments", "colour")
        # And adding it again is a no-op, so a restored backup recovers.
        assert migrations.add_column(conn, "shipments", "colour VARCHAR(16)") is False

    fresh_engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    Base.metadata.create_all(bind=fresh_engine)
    assert migrations.run(fresh_engine, fresh=True) == STEPS + [NEXT]
    assert ran == [f"{NEXT:03d}"], "a fresh database is stamped, the step must not run"


def test_a_failed_step_leaves_the_version_where_it_was(tmp_path, monkeypatch):
    def _004_explodes(conn):
        conn.execute(text("SELECT * FROM no_such_table"))

    monkeypatch.setattr(migrations, "MIGRATIONS",
                        migrations.MIGRATIONS + [(NEXT, "explodes", _004_explodes)])
    old_engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    User.__table__.create(old_engine)
    with pytest.raises(Exception):
        migrations.run(old_engine, fresh=False)
    assert migrations.current(old_engine) == STEPS[-1]


# --- the settings answer -------------------------------------------------------


def test_public_settings_say_whether_shipments_are_kept(db, monkeypatch):
    assert settings_store.public_settings(db).history_enabled is False
    monkeypatch.setenv("CARGOPILOT_HISTORY", "true")
    get_settings.cache_clear()
    assert settings_store.public_settings(db).history_enabled is True
