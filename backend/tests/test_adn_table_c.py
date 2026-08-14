"""The tank vessel table, and the promises its seed makes.

``adn_table_c.json`` is the first seed in this repository read from three
*editions* — the row set and every cell from the UNECE English PDF, the
corroboration and the Dutch names from the mindef export, and the UNECE French
edition, the treaty's other authentic language, as the third voice. The
comparison is not a formality it passed but a record it carries: a cell no two
readings agree on is stored with every value read, under ``disputed``, and
counts as not settled. These tests pin that record to the data, so the seed
cannot drift into looking more certain than it is.
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


def test_een_betwiste_cel_draagt_alle_waarden():
    """A disputed cell names which edition read what, and at least two of them:
    a dispute is a disagreement between readings, so one value is not one."""
    for entry in seed()["entries"]:
        for field, sides in (entry.get("disputed") or {}).items():
            assert set(sides) <= {"en", "nl", "fr"}, (entry["un"], field)
            assert len(sides) >= 2, (entry["un"], field)
            assert field in entry, (entry["un"], field)


def test_de_export_splitsing_is_teruggevouwen():
    """UN 1268 prints 26 rows whose name offers two alternatives each; the
    Dutch export split them into 52. The seed holds the printed 26, with both
    Dutch names joined on."""
    rows = [e for e in seed()["entries"] if e["un"] == "1268"]
    assert len(rows) == 26
    assert any("/" in row["name_nl"] for row in rows)


def test_wat_de_export_mist_leest_de_franse_uitgave():
    """UN 1977 and UN 1999 are absent from the Dutch export and present in the
    book. Before the French reading they rested on one reading; now the French
    edition corroborates them, and they carry a French name and no Dutch one."""
    for un in ("1977", "1999"):
        rows = [e for e in seed()["entries"] if e["un"] == un]
        assert rows, un
        assert all(row["readings"] >= 2 for row in rows), un
        assert all(row["name_fr"] for row in rows), un
        assert all(not row.get("name_nl") for row in rows), un


def test_de_derde_lezing_heeft_de_engelse_cel_niet_omvergestemd():
    """Where the French reading decided a stand-off it sided with the English
    edition every time — 180 cells, none overturned. The seed says so, and the
    rows agree: a field the record calls settled by the French reading is not
    also disputed."""
    data = seed()
    check = data["cross_check"]
    assert check["cells_the_french_reading_overturned"] == 0
    settled = sum(len(e.get("settled_by_french") or {}) for e in data["entries"])
    assert settled == check["cells_settled_by_the_french_reading"]
    for entry in data["entries"]:
        for field in (entry.get("settled_by_french") or {}):
            assert field not in (entry.get("disputed") or {}), entry["un"]


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
    """UN 1208's sampling device is read as 2 by the English edition and as 3
    by the French, with no Dutch row to break the tie. The database must hold
    that cell back rather than choose a side, while the cells around it —
    settled by all three readings — still answer."""
    entries = [e for e in seed()["entries"] if e["un"] == "1208"]
    disputed = [e for e in entries if "sampling_device" in (e.get("disputed") or {})]
    assert len(disputed) == 1
    assert set(disputed[0]["disputed"]["sampling_device"]) == {"en", "fr"}

    # The cells the three readings do settle still answer, dispute or no.
    answer = database.adn_tank_vessel_answer("1208")
    assert answer["vessel_type"] == "N"
    rows = database.adn_table_c_rows("1208")
    assert any(row.get("disputed") for row in rows)
