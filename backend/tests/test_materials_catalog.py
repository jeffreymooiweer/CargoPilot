"""De goederendatabase, en de eigenschappen waar de rest van de app op leunt.

Deze database is gegroeid van 400 naar ruim 1.000 goederen. Bij 400 kon je er
nog met het oog naar kijken; bij 1.000 niet meer, en juist dan sluipen de fouten
erin die niemand opmerkt omdat ze eruitzien als een gewone regel.

Wat hier wordt vastgelegd, en waarom telkens:

- **Geen twee vermeldingen van hetzelfde goed.** De gebruiker kiest er één, en
  welke hij kiest bepaalt zijn gewicht. Tijdens de uitbreiding bleken achttien
  kandidaten een bestaand goed te herhalen — dat is niet zichtbaar aan de
  vermelding zelf, alleen aan de botsing.
- **Geen alias die twee goederen tegelijk claimt.** Een alias is een zoeksleutel;
  als twee goederen dezelfde sleutel dragen, beslist de volgorde in de database
  wie er wint, en dat is geen antwoord maar toeval.
- **Drie talen, altijd.** `test_languages.py` bewaakt dat al voor élk bestand met
  vertaalde tekst; hier staat het nog eens per goed, omdat de naam die de
  gebruiker aanklikt de omschrijving op zijn vrachtbrief wordt.
- **Een categorie die `units.py` kent.** De categorie bepaalt de
  dichtheidsgrondslag (stort, vloeistof, massief, gestapeld) en welke eenheden de
  goederenstap aanbiedt. Een categorie die daar niet in staat valt stilzwijgend
  terug op de standaard — 20 m³ grind maal een massieve dichtheid is precies de
  fout waar `units.py` voor bestaat.
- **De dichtheid ligt binnen zijn eigen bandbreedte.** Een tikfout in min of max
  maakt de opgegeven waarde onmogelijk zonder dat er iets omvalt.
"""

import json
from pathlib import Path

import pytest

from app.services.units import BASIS_BY_CATEGORY

SEED = Path(__file__).resolve().parents[1] / "seed" / "materials.json"
MATERIALS = json.loads(SEED.read_text(encoding="utf-8"))


def test_de_database_is_flink_gegroeid_en_blijft_dat():
    """Een ondergrens, zodat een half doorgevoerde samenvoeging opvalt."""
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
    """Anders valt de dichtheidsgrondslag stil terug op de standaard."""
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
    """Nul zou een deling verderop stilzwijgend laten ontsporen."""
    wrong = [item["canonical_name"] for item in MATERIALS if item["density_kg_m3"] <= 0]

    assert wrong == []


def test_de_dichtheden_blijven_binnen_wat_natuurkundig_kan():
    """Ruime grenzen: lichter dan piepschuim of zwaarder dan iridium is een tikfout.

    Iridium (22.560 kg/m³) is het zwaarste dat hier staat en EPS-korrels (20)
    het lichtste. De grenzen liggen er ruim omheen; deze test vangt een
    verdwaalde nul, geen discussie over de derde decimaal.
    """
    outliers = [
        (item["canonical_name"], item["density_kg_m3"])
        for item in MATERIALS
        if not 5 <= item["density_kg_m3"] <= 25000
    ]

    assert outliers == []


def test_de_talen_verschillen_waar_de_woorden_verschillen():
    """Een steekproef die aantoont dat er echt vertaald is en niet gekopieerd.

    Sommige goederen heten in drie talen hetzelfde — "Aluminium", "Merbau",
    "Bulgur" — en dat is juist. Maar als het overgrote deel identiek zou zijn,
    was er niet vertaald maar geplakt, en dan is de Duitse kolom een belofte die
    niet wordt waargemaakt.
    """
    differing = [
        item
        for item in MATERIALS
        if len({v.lower() for v in item["language_labels"].values()}) > 1
    ]

    assert len(differing) > len(MATERIALS) * 0.6
