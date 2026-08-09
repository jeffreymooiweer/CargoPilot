"""Not every consignment needs dimensions to be worked out.

"1500 litres of petrol" is fully determined: the unit gives the volume, the
density of the recognised commodity gives the mass. Yet the application reported
"dimensions_missing" and weight and volume stayed empty, while everything needed
to work it out was on the screen.

The cause is the kind worth recording: the units module of v1.34.0 *was* used by
the dropdown and not by the calculation. There was a neat list of units, an API
to compute with them, and a pipeline that never asked for it. Half connected is
not connected.
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
    """745 kg/m³ times 1.5 m³. No length, width or height is needed for it."""
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
    """The unit was a free text field for years; "liter" simply has to work."""
    assert line(db, "Diesel | 1000 | liter")["weight_total_kg"] == pytest.approx(840.0)


def test_an_unrecognised_substance_is_not_given_the_density_of_steel(db):
    """match_material falls back to steel when nothing fits. Without this limit
    1500 litres of an unknown substance would weigh 11,775 kg — a figure that
    looks just as confident as the answer that is right."""
    result = line(db, "Onbekendestof | 1500 | l")
    assert result["weight_total_kg"] is None
    assert "material_not_recognized" in result["messages"]


def test_a_line_without_a_usable_unit_still_says_what_is_missing(db):
    """Fifteen pallets without a weight per pallet stay unknown: a count carries
    no physics in itself."""
    result = line(db, "Pallets diversen | 15 | pallet")
    assert result["weight_total_kg"] is None
    assert "dimensions_missing" in result["messages"]


def test_dimensions_still_win_where_they_exist(db):
    """A steel plate with dimensions is still computed from those dimensions; the
    unit only steps in when there is nothing else."""
    result = line(db, "Stalen plaat 2000x1000x10 mm | 2 | stuks")
    assert result["weight_total_kg"] is not None
    assert result["weight_total_kg"] > 0
