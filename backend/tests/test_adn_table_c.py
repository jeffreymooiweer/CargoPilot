"""The tank vessel table, and the promises its seed makes.

``adn_table_c.json`` is the first seed in this repository read from three
*books*: the row set and every cell from the UNECE English PDF, the
corroboration and the Dutch names from the printed Dutch edition, and the UNECE
French edition, the treaty's other authentic language, as the third voice. The
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


def test_de_or_naam_staat_in_een_rij():
    """UN 1268 prints 26 rows whose name offers two alternatives each. The
    export the Dutch reading used to come from split them into 52 and this
    seed had to fold them back; the printed edition prints what it prints, and
    the alternative stands inside the name where the book puts it."""
    rows = [e for e in seed()["entries"] if e["un"] == "1268"]
    assert len(rows) == 26
    assert all(" of " in row["name_nl"] for row in rows)


def test_wat_de_export_miste_staat_in_het_boek():
    """UN 1977 and UN 1999 were absent from the HTML export the Dutch reading
    used to come from — they rested on the English edition alone, and then on
    the French as second. The printed Dutch edition has them like any other
    row: three readings and a name in every language."""
    for un in ("1977", "1999"):
        rows = [e for e in seed()["entries"] if e["un"] == un]
        assert rows, un
        assert all(row["readings"] == 3 for row in rows), un
        assert all(row["name_fr"] and row["name_nl"] for row in rows), un


def test_de_derde_lezing_beslecht_en_zegt_welke_kant():
    """Where the French reading decides a stand-off the record says which of
    the first two it sided with, and a cell it settled is not also disputed.
    With the Dutch reading coming from the export it sided with the English
    edition 180 times out of 180; from the printed book there are 27 such
    cells and one of them went the other way — UN 2672's density."""
    data = seed()
    check = data["cross_check"]
    overturned = [e["un"] for e in data["entries"]
                  if "nl" in (e.get("settled_by_french") or {}).values()]
    assert len(overturned) == check["cells_the_french_reading_overturned"]
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
    """One cell in the whole table has no two readings agreeing: UN 2789's
    density, where all three editions print 1,05 and then qualify it in their
    own language. The database must hold that cell back rather than choose a
    side, while the cells around it still answer."""
    entries = [e for e in seed()["entries"] if e["un"] == "2789"]
    disputed = [e for e in entries if "density" in (e.get("disputed") or {})]
    assert len(disputed) == 1
    assert set(disputed[0]["disputed"]["density"]) == {"en", "nl", "fr"}

    # The cells the three readings do settle still answer, dispute or no.
    assert database.adn_tank_vessel_answer("2789")["vessel_type"] == "N"
    rows = database.adn_table_c_rows("2789")
    assert any(row.get("disputed") for row in rows)
