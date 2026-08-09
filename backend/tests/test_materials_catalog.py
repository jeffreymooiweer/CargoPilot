"""The goods database, and the properties the rest of the app leans on.

This database has grown from 400 to well over 1,000 commodities. At 400 you could
still look at it with the naked eye; at 1,000 you cannot, and that is exactly
when the faults creep in that nobody spots because they look like an ordinary row.

What is recorded here, and why each time:

- **No two entries of the same commodity.** The user picks one, and which one
  they pick determines their weight. During the expansion eighteen candidates
  turned out to repeat an existing commodity — that is not visible from the entry
  itself, only from the collision.
- **No alias claiming two commodities at once.** An alias is a search key; if two
  commodities carry the same key, the order in the database decides who wins, and
  that is not an answer but coincidence.
- **Three languages, always.** `test_languages.py` already guards that for
  *every* file with translated text; here it is stated once more per commodity,
  because the name the user clicks becomes the description on their waybill.
- **A category `units.py` knows.** The category determines the density basis
  (bulk, liquid, solid, stacked) and which units the goods step offers. A
  category that is not in there falls back silently to the default — 20 m³ of
  gravel times a solid density is precisely the fault `units.py` exists for.
- **The density lies within its own band.** A typo in min or max makes the stated
  value impossible without anything falling over.
"""

import json
from pathlib import Path

import pytest

from app.services.units import BASIS_BY_CATEGORY

SEED = Path(__file__).resolve().parents[1] / "seed" / "materials.json"
MATERIALS = json.loads(SEED.read_text(encoding="utf-8"))


def test_de_database_is_flink_gegroeid_en_blijft_dat():
    """A lower bound, so a half-completed merge stands out."""
    assert len(MATERIALS) >= 1000


def test_elk_goed_komt_maar_een_keer_voor():
    names = [item["canonical_name"] for item in MATERIALS]

    duplicates = sorted({name for name in names if names.count(name) > 1})

    assert duplicates == []


def test_geen_alias_hoort_bij_twee_goederen():
    owner: dict[str, str] = {}
    clashes: list[str] = []
    for item in MATERIALS:
        for alias in item.get("aliases", []):
            key = alias.strip().lower()
            if key in owner:
                clashes.append(f"{alias!r}: {owner[key]} en {item['canonical_name']}")
            owner[key] = item["canonical_name"]

    assert clashes == []


@pytest.mark.parametrize("language", ["nl", "en", "de"])
def test_elk_goed_heeft_een_naam_in_alle_drie_de_talen(language):
    missing = [
        item["canonical_name"]
        for item in MATERIALS
        if not str(item.get("language_labels", {}).get(language) or "").strip()
    ]

    assert missing == []


def test_elke_categorie_is_er_een_die_units_kent():
    """Otherwise the density basis falls back quietly to the default."""
    unknown = sorted({
        item["category"] for item in MATERIALS if item["category"] not in BASIS_BY_CATEGORY
    })

    assert unknown == []


def test_de_dichtheid_ligt_tussen_het_minimum_en_het_maximum():
    impossible = [
        item["canonical_name"]
        for item in MATERIALS
        if not (
            item.get("density_min_kg_m3", item["density_kg_m3"])
            <= item["density_kg_m3"]
            <= item.get("density_max_kg_m3", item["density_kg_m3"])
        )
    ]

    assert impossible == []


def test_geen_enkele_dichtheid_is_nul_of_negatief():
    """Zero would let a division further along go off the rails silently."""
    wrong = [item["canonical_name"] for item in MATERIALS if item["density_kg_m3"] <= 0]

    assert wrong == []


def test_de_dichtheden_blijven_binnen_wat_natuurkundig_kan():
    """Generous bounds: lighter than polystyrene or heavier than iridium is a typo.

    Iridium (22,560 kg/m³) is the heaviest thing in here and EPS beads (20) the
    lightest. The bounds sit well outside those; this test catches a stray zero,
    not a discussion about the third decimal.
    """
    outliers = [
        (item["canonical_name"], item["density_kg_m3"])
        for item in MATERIALS
        if not 5 <= item["density_kg_m3"] <= 25000
    ]

    assert outliers == []


def test_de_talen_verschillen_waar_de_woorden_verschillen():
    """A sample showing there was really translation and not copying.

    Some commodities are called the same in three languages — "Aluminium",
    "Merbau", "Bulgur" — and that is right. But if the vast majority were
    identical, there had been no translation but pasting, and then the German
    column is a promise that is not kept.
    """
    differing = [
        item
        for item in MATERIALS
        if len({v.lower() for v in item["language_labels"].values()}) > 1
    ]

    assert len(differing) > len(MATERIALS) * 0.6
