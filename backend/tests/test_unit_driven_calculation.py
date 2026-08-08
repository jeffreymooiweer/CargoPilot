"""Niet elke zending heeft afmetingen nodig om uitgerekend te worden.

"1500 liter benzine" is volledig bepaald: de eenheid geeft het volume, het
soortelijk gewicht van het herkende goed geeft de massa. Toch meldde de
applicatie "dimensions_missing" en bleven gewicht en volume leeg, terwijl alles
om het uit te rekenen op het scherm stond.

De oorzaak is het soort dat de moeite van het vastleggen waard is: de
eenhedenmodule van v1.34.0 werd wél gebruikt door de keuzelijst en niet door de
berekening. Er was een nette lijst eenheden, een API om ermee te rekenen, en een
pijplijn die er nooit naar vroeg. Half aangesloten is niet aangesloten.
"""

import pytest

from app.core.database import SessionLocal
from app.services.pipeline import parse_and_calculate


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def line(db, text: str) -> dict:
    return parse_and_calculate(text, db=db)["lines"][0]


def test_fifteen_hundred_litres_of_petrol_is_enough_to_calculate(db):
    """745 kg/m³ maal 1,5 m³. Er is geen lengte, breedte of hoogte voor nodig."""
    result = line(db, "Benzine | 1500 | l")
    assert result["weight_total_kg"] == pytest.approx(1117.5)
    assert result["transport_volume_m3"] == pytest.approx(1.5)
    assert result["status"] == "ok"
    assert "dimensions_missing" not in result["messages"]


def test_a_mass_unit_gives_the_volume_back(db):
    result = line(db, "Grind | 20 | ton")
    assert result["weight_total_kg"] == pytest.approx(20000.0)
    assert result["transport_volume_m3"] == pytest.approx(20000.0 / 1700, rel=0.05)
    assert result["status"] == "ok"


def test_the_spellings_people_type_still_arrive_at_the_calculation(db):
    """De eenheid was jarenlang een vrij tekstveld; "liter" moet gewoon werken."""
    assert line(db, "Diesel | 1000 | liter")["weight_total_kg"] == pytest.approx(840.0)


def test_an_unrecognised_substance_is_not_given_the_density_of_steel(db):
    """match_material valt terug op staal wanneer niets past. Zonder deze grens
    zou 1500 liter van een onbekende stof 11 775 kg wegen — een getal dat er even
    stellig uitziet als het antwoord dat klopt."""
    result = line(db, "Onbekendestof | 1500 | l")
    assert result["weight_total_kg"] is None
    assert "material_not_recognized" in result["messages"]


def test_a_line_without_a_usable_unit_still_says_what_is_missing(db):
    """Vijftien pallets zonder gewicht per pallet blijven onbekend: een aantal
    draagt geen natuurkunde in zich."""
    result = line(db, "Pallets diversen | 15 | pallet")
    assert result["weight_total_kg"] is None
    assert "dimensions_missing" in result["messages"]


def test_dimensions_still_win_where_they_exist(db):
    """Een stalen plaat met afmetingen wordt nog steeds uit die afmetingen
    gerekend; de eenheid springt alleen bij wanneer er niets anders is."""
    result = line(db, "Stalen plaat 2000x1000x10 mm | 2 | stuks")
    assert result["weight_total_kg"] is not None
    assert result["weight_total_kg"] > 0
