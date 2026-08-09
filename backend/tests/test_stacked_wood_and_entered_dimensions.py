"""A cubic metre of stacked timber is not a cubic metre of timber, and
measurements do not belong in the name.

Two complaints from practice, and they are connected: both are about the
difference between what was entered and what the application made of it.

**Timber.** The density of oak is 720 kg/m³ and that is the density of the wood
itself. Between the planks of a stack there is air. Anyone entering 20 m³ of oak
got 14,400 kg back — the weight of 20 m³ of solid oak, which almost nobody
carries.

v1.35.0 solved that with one hidden factor of 0.65 for all timber. That was an
average describing nobody's load: loose firewood is lighter, a tight bundle
heavier. Since v1.36.0 the user picks the **form** and the form carries the
factor — and that applies just as much to steel (plate against scrap) and plastic
(granulate against regrind).

**Dimensions.** Length, width and height had to be hidden in the description
("balk 200x200x3000") because the calculation paths looked only at what had been
read out of the text. The columns you could fill them in worked through to the
display only.
"""

import pytest

from app.core.database import SessionLocal
from app.services.pipeline import parse_and_calculate
from app.services.units import (
    available_forms,
    convert,
    default_form,
    effective_density,
    fill_factor,
    form_applies,
)


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
    """720 kg/m³ times 0.65 is 468 kg/m³ for the stack as it is carried."""
    result = line(db, "Eiken | 20 | m3")
    assert result["weight_total_kg"] == pytest.approx(9360.0)
    assert result["weight_total_kg"] < 20 * 720  # not computed as solid


def test_sheet_material_stacks_flat_and_keeps_its_own_density(db):
    """Plates lie on top of each other without a gap; there is nothing to take off."""
    assert line(db, "Multiplex | 20 | m3")["weight_total_kg"] == pytest.approx(13000.0)


@pytest.mark.parametrize("name", ["plywood", "osb", "mdf", "hdf", "chipboard", "clt", "glulam"])
def test_sheet_material_defaults_to_lying_flat(name):
    assert default_form("wood", name).value == "sheets"
    assert fill_factor("wood", name) == 1.0


@pytest.mark.parametrize("name", ["oak", "spruce", "pine", "logs", "firewood", "teak"])
def test_sawn_and_round_timber_defaults_to_stacked(name):
    assert default_form("wood", name).value == "stacked"
    assert fill_factor("wood", name) == pytest.approx(0.65)


@pytest.mark.parametrize(
    "form,expected",
    [("solid", 14400.0), ("bundled", 10800.0), ("stacked", 9360.0), ("loose", 6480.0)],
)
def test_the_chosen_form_decides_the_weight(form, expected):
    """One average describes nobody's load; loose firewood is lighter than a
    tight bundle and the user may say so themselves."""
    assert convert(20, "m3", 720, "wood", canonical_name="oak", form=form).mass_kg == (
        pytest.approx(expected)
    )


def test_the_form_never_double_counts_a_bulk_density():
    """For gravel the stored figure is already a bulk density. Laying "loose
    bulk" over that as well would subtract the air twice."""
    assert not form_applies("bulk_material")
    assert available_forms("bulk_material") == []
    assert convert(20, "m3", 1600, "bulk_material", form="loose").mass_kg == 32000.0
    assert effective_density(1600, "bulk_material", form="loose") == 1600


def test_a_liquid_has_no_form_either():
    assert available_forms("liquid") == []
    assert convert(1000, "l", 745, "liquid", form="loose").mass_kg == pytest.approx(745.0)


def test_steel_offers_the_same_choice_as_timber():
    """Plate against scrap is the same distinction as beam against stacked
    timber, and it makes just as much difference."""
    forms = [form.value for form in available_forms("metal")]
    assert "solid" in forms and "loose" in forms
    assert default_form("metal").value == "solid"
    plate = convert(2, "m3", 7850, "metal", form="solid").mass_kg
    scrap = convert(2, "m3", 7850, "metal", form="loose").mass_kg
    assert plate == pytest.approx(15700.0)
    assert scrap == pytest.approx(7065.0)


def test_the_density_actually_used_is_reported():
    """A user wondering where 9,360 kg comes from should be able to see it: it
    was computed with 468 kg/m³ and not with 720."""
    out = convert(20, "m3", 720, "wood", canonical_name="oak")
    assert out.density_used_kg_m3 == pytest.approx(468.0)
    assert out.fill_factor == pytest.approx(0.65)
    assert out.form == "stacked"


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
    """With measurements given, the volume is the volume of the timber itself;
    the stacking factor precisely does not belong there. Only whoever enters
    cubic metres buys air along with it."""
    result = line(
        db, "Eiken balk | 1 | stuks",
        {"line_id": 1, "width_m": 0.2, "height_m": 0.2, "length_m": 3.0},
    )
    assert result["weight_total_kg"] == pytest.approx(0.12 * 720)


def test_the_description_no_longer_has_to_carry_the_measurements(db):
    """The same beam, once via the name and once via the columns."""
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
    """An HEA 200 has a weight per metre; only the length is still missing."""
    result = line(db, "HEA 200 | 3 | stuks", {"line_id": 1, "length_m": 6.0})
    assert result["weight_total_kg"] is not None
    assert result["weight_total_kg"] > 0


def test_a_partial_set_of_dimensions_does_not_silently_become_a_volume(db):
    """Two of the three measurements is not a block. Nothing is computed from it
    rather than multiplying by an invented third measurement."""
    result = line(
        db, "Onbekendestof plaat | 1 | stuks",
        {"line_id": 1, "width_m": 2.0, "height_m": 1.0},
    )
    assert result["weight_total_kg"] is None
