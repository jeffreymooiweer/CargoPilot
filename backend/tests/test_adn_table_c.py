"""The tank vessel table, and the promises its seed makes.

``adn_table_c.json`` is the first seed in this repository whose two readings
came from two *editions* — the row set and every cell from the UNECE English
PDF, the corroboration and the Dutch names from the mindef export — and the
comparison is not a formality it passed but a record it carries: rows the
Dutch export lacks say ``readings: 1``, and a cell the two readings give
differently is stored with both values under ``disputed`` and counts as not
settled. These tests pin that record to the data, so the seed cannot drift
into looking more certain than it is.
"""
import json
from pathlib import Path

from app.services.dg import database

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg" / "adn_table_c.json"


def seed():
    return json.loads(SEED.read_text(encoding="utf-8"))


def test_de_boekhouding_klopt_met_de_rijen():
    data = seed()
    entries = data["entries"]
    check = data["cross_check"]
    assert len(entries) == check["rows"]
    assert sum(1 for e in entries if e["readings"] == 1) == check["rows_read_once"]
    assert (sum(1 for e in entries if e.get("disputed"))
            == check["rows_with_disputed_cells"])
    assert (check["settled_rows"] + check["rows_with_disputed_cells"]
            + check["rows_read_once"] == check["rows"])


def test_een_betwiste_cel_draagt_beide_waarden():
    for entry in seed()["entries"]:
        for field, sides in (entry.get("disputed") or {}).items():
            assert set(sides) == {"en", "nl"}, (entry["un"], field)
            assert field in entry, (entry["un"], field)


def test_de_export_splitsing_is_teruggevouwen():
    """UN 1268 prints 26 rows whose name offers two alternatives each; the
    Dutch export split them into 52. The seed holds the printed 26, with both
    Dutch names joined on."""
    rows = [e for e in seed()["entries"] if e["un"] == "1268"]
    assert len(rows) == 26
    assert any("/" in row["name_nl"] for row in rows)


def test_wat_de_export_mist_staat_er_toch_in():
    """UN 1977 and UN 1999 are absent from the Dutch export and present in the
    book; the seed carries them on one reading and says so."""
    for un in ("1977", "1999"):
        rows = [e for e in seed()["entries"] if e["un"] == un]
        assert rows, un
        assert all(row["readings"] == 1 for row in rows), un


def test_de_databank_middelt_geen_varianten():
    """Petrol's six rows split between vessel types N and C; the answer is the
    list, never a pick. The cones agree across all six, so that one settles."""
    answer = database.adn_tank_vessel_answer("1203")
    assert answer["vessel_type"] is None
    assert answer["vessel_types_seen"] == ["C", "N"]
    assert answer["cones"] == "1"

    assert database.adn_tank_vessel_answer("1005")["vessel_type"] == "G"
    assert database.adn_tank_vessel_answer("0004") is None


def test_een_betwiste_cel_is_geen_antwoord():
    """Somewhere in the seed a cones cell is disputed; the database must
    withhold the cones for that substance, not choose a side."""
    disputed_cones = [
        e["un"] for e in seed()["entries"]
        if "blue_cones" in (e.get("disputed") or {})]
    assert disputed_cones, "the comparison record lost its disputed cones rows"
    un = disputed_cones[0]
    answer = database.adn_tank_vessel_answer(un)
    assert answer["cones"] is None
