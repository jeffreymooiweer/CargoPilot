"""Een kuub gestapeld hout is geen kuub hout, en maten horen niet in de naam.

Twee klachten uit de praktijk, en ze hangen samen: allebei gaan ze over het
verschil tussen wat er is ingevoerd en wat de applicatie daarvan maakte.

**Hout.** De dichtheid van eiken is 720 kg/m³ en dat is de dichtheid van het
hout zelf. Tussen de planken van een stapel zit lucht. Wie 20 m³ eiken invoerde
kreeg 14 400 kg terug — het gewicht van 20 m³ massief eiken, wat vrijwel niemand
vervoert. Plaatmateriaal is de uitzondering, want platen stapelen vlak.

**Afmetingen.** Lengte, breedte en hoogte moesten in de omschrijving worden
verstopt ("balk 200x200x3000") omdat de rekenpaden alleen keken naar wat er uit
de tekst was gelezen. De kolommen waarin je ze kon invullen werkten alleen door
naar de weergave.
"""

import pytest

from app.core.database import SessionLocal
from app.services.pipeline import parse_and_calculate
from app.services.units import convert, stacked_density, stacking_factor


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def line(db, text: str, overrides: dict | None = None) -> dict:
    return parse_and_calculate(
        text, db=db, line_overrides=[overrides] if overrides else None
    )["lines"][0]


# --- Gestapeld hout -------------------------------------------------------


def test_a_cubic_metre_of_stacked_oak_is_not_a_cubic_metre_of_oak(db):
    """720 kg/m³ maal 0,65 is 468 kg/m³ voor de stapel zoals hij vervoerd wordt."""
    result = line(db, "Eiken | 20 | m3")
    assert result["weight_total_kg"] == pytest.approx(9360.0)
    assert result["weight_total_kg"] < 20 * 720  # niet massief gerekend


def test_sheet_material_stacks_flat_and_keeps_its_own_density(db):
    """Platen liggen op elkaar zonder tussenruimte; daar valt niets af te halen."""
    assert line(db, "Multiplex | 20 | m3")["weight_total_kg"] == pytest.approx(13000.0)


@pytest.mark.parametrize("name", ["plywood", "osb", "mdf", "hdf", "chipboard", "clt", "glulam"])
def test_every_sheet_like_product_is_treated_as_solid(name):
    assert stacking_factor("wood", name) == 1.0


@pytest.mark.parametrize("name", ["oak", "spruce", "pine", "logs", "firewood", "teak"])
def test_sawn_and_round_timber_gets_the_stacking_factor(name):
    assert stacking_factor("wood", name) == pytest.approx(0.65)


def test_nothing_but_wood_is_stacked():
    """Grind is stortgoed en heeft al een stortdichtheid; daar mag niets af."""
    assert stacking_factor("bulk_material", "gravel") == 1.0
    assert stacking_factor("metal", "steel") == 1.0
    assert stacked_density(1600, "bulk_material") == 1600


def test_the_density_actually_used_is_reported():
    """Een gebruiker die zich afvraagt waar 9 360 kg vandaan komt, hoort het te
    kunnen zien: er is met 468 kg/m³ gerekend en niet met 720."""
    out = convert(20, "m3", 720, "wood", canonical_name="oak")
    assert out.density_used_kg_m3 == pytest.approx(468.0)
    assert out.stacking_factor == pytest.approx(0.65)
    assert out.basis.value == "stacked"


# --- Ingevulde afmetingen -------------------------------------------------


def test_dimensions_from_the_table_drive_the_calculation(db):
    """0,2 x 0,2 x 3 m eiken is 0,12 m³ massief hout, 86,4 kg per stuk."""
    result = line(
        db, "Eiken balk | 4 | stuks",
        {"line_id": 1, "width_m": 0.2, "height_m": 0.2, "length_m": 3.0},
    )
    assert result["weight_total_kg"] == pytest.approx(345.6)
    assert result["transport_volume_m3"] == pytest.approx(0.48)
    assert result["status"] == "ok"


def test_a_beam_with_dimensions_is_solid_not_stacked(db):
    """Bij opgegeven maten is het volume het volume van het hout zelf; daar hoort
    de stapelfactor juist niet bij. Alleen wie in kuubs invoert koopt lucht mee."""
    result = line(
        db, "Eiken balk | 1 | stuks",
        {"line_id": 1, "width_m": 0.2, "height_m": 0.2, "length_m": 3.0},
    )
    assert result["weight_total_kg"] == pytest.approx(0.12 * 720)


def test_the_description_no_longer_has_to_carry_the_measurements(db):
    """Dezelfde balk, één keer via de naam en één keer via de kolommen."""
    from_name = line(db, "Stalen plaat 2000x1000x10 mm | 1 | stuks")
    from_fields = line(
        db, "Stalen plaat | 1 | stuks",
        {"line_id": 1, "width_m": 2.0, "height_m": 1.0, "length_m": 0.01},
    )
    assert from_fields["weight_total_kg"] == pytest.approx(from_name["weight_total_kg"])


def test_entered_dimensions_are_echoed_back_in_centimetres(db):
    result = line(
        db, "Eiken balk | 1 | stuks",
        {"line_id": 1, "width_m": 0.2, "height_m": 0.25, "length_m": 3.0},
    )
    assert result["length_cm"] == pytest.approx(300.0)
    assert result["width_cm"] == pytest.approx(20.0)
    assert result["height_cm"] == pytest.approx(25.0)


def test_a_length_on_its_own_is_enough_for_a_catalogue_profile(db):
    """Een HEA 200 heeft een gewicht per meter; alleen de lengte ontbreekt nog."""
    result = line(db, "HEA 200 | 3 | stuks", {"line_id": 1, "length_m": 6.0})
    assert result["weight_total_kg"] is not None
    assert result["weight_total_kg"] > 0


def test_a_partial_set_of_dimensions_does_not_silently_become_a_volume(db):
    """Twee van de drie maten is geen blok. Er wordt dan niets uit gerekend in
    plaats van met een verzonnen derde maat te vermenigvuldigen."""
    result = line(
        db, "Onbekendestof plaat | 1 | stuks",
        {"line_id": 1, "width_m": 2.0, "height_m": 1.0},
    )
    assert result["weight_total_kg"] is None
