"""The shunting-model rows of RID table A column (5), sealed as a seed.

Extracted geometrically from the OTIF English edition and the German edition
by scripts/extract_rid_shunting_labels.py (workflow runs 32248906310 and
32248925966), which agree on every one of the 351 rows. The first probe run
is worth remembering: the plain (13) and (15) it matched were the table's own
column headers, printed on every page — the cells print (+13) and (+15), and
the plus sign is the discriminator.
"""
import json
from pathlib import Path

from app.services.dg.database import rid_shunting_models

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg" / \
    "rid_shunting_labels.json"


def rows():
    return json.loads(SEED.read_text(encoding="utf-8"))["rows"]


def test_the_seed_holds_the_agreed_reading():
    data = rows()
    assert len(data) == 351
    assert all(set(models) <= {"13", "15"} and models for models in data.values())


def test_every_marked_substance_is_class_1_or_2():
    """The column (5) explanation names exactly two cases, and the extraction
    should land on exactly those classes — checked against the application's
    own table A."""
    from app.services.dg import database
    classes = set()
    for un in rows():
        entries = database.get_un_entries(un)
        assert entries, f"UN {un} marked but not in table A"
        classes.add(str(entries[0].get("class")))
    assert classes == {"1", "2"}


def test_the_sixteen_model_15_rows_are_class_1():
    """Model 15 — loose or hump shunting forbidden — brackets sixteen
    substances, every one a division 1.1 explosive."""
    fifteens = [un for un, models in rows().items() if models == ["15"]]
    assert len(fifteens) == 16
    assert all(un.startswith("0") for un in fifteens)


def test_the_accessor_tells_absence_apart_from_unread():
    assert rid_shunting_models("1017") == ["13"]
    assert rid_shunting_models("0027") == ["13"]
    assert rid_shunting_models("0072") == ["15"]
    # A substance the book brackets nothing for: a real absence, not None.
    assert rid_shunting_models("1203") == []
    assert rid_shunting_models("") == []
