"""A quantity without a unit means nothing.

The unit of a line was a free text field with "stuks" as the default. Whoever
entered 1200 litres of diesel got 1200 pieces of diesel and could look up the
weight themselves. These tests record that a quantity now has a dimension, and
that density bridges mass and volume.

The second theme is as important as the first: where it *cannot* be computed, it
is not computed. Forty pallets without a weight per pallet weigh an unknown
number of kilos. Making that 0 produces a total that looks fine and means
nothing — the same fault as showing a check that did not run as a check that
passed.
"""

import pytest

from app.services.units import (
    DensityBasis,
    Dimension,
    convert,
    default_unit,
    density_basis,
    format_quantity,
    get_unit,
    suggested_units,
)

DIESEL = 835.0      # kg/m³
GRAVEL = 1600.0     # stortdichtheid
STEEL = 7850.0


# --- The bridge between mass and volume -----------------------------------


def test_litres_of_a_liquid_become_kilograms():
    out = convert(1200, "l", DIESEL, "liquid")
    assert out.volume_m3 == pytest.approx(1.2)
    assert out.mass_kg == pytest.approx(1002.0)
    assert out.missing is None


def test_tonnes_of_bulk_become_cubic_metres():
    out = convert(20, "ton", GRAVEL, "bulk_material")
    assert out.mass_kg == pytest.approx(20000.0)
    assert out.volume_m3 == pytest.approx(12.5)


def test_cubic_metres_of_bulk_become_tonnes():
    out = convert(20, "m3", GRAVEL, "bulk_material")
    assert out.volume_m3 == pytest.approx(20.0)
    assert out.mass_kg == pytest.approx(32000.0)


def test_the_same_volume_of_steel_is_a_different_mass():
    """Trivial, and exactly the point: the unit alone says nothing about weight."""
    assert convert(5, "m3", STEEL, "metal").mass_kg == pytest.approx(39250.0)
    assert convert(5, "m3", GRAVEL, "bulk_material").mass_kg == pytest.approx(8000.0)


def test_without_a_density_only_the_entered_side_is_filled():
    out = convert(500, "kg", None, None)
    assert out.mass_kg == pytest.approx(500.0)
    assert out.volume_m3 is None
    assert out.missing == "density"


# --- Where it cannot be computed, it is not computed -----------------------


def test_a_count_without_a_weight_per_item_reports_that():
    out = convert(40, "pallet", None, "general_cargo")
    assert out.mass_kg is None and out.volume_m3 is None
    assert out.missing == "per_item"


def test_a_count_with_a_weight_per_item_is_multiplied():
    out = convert(40, "pallet", None, "general_cargo", mass_per_item_kg=300)
    assert out.mass_kg == pytest.approx(12000.0)
    assert out.missing is None


def test_a_count_with_a_volume_per_item_and_a_density_gives_both():
    out = convert(10, "box", 400.0, "food", volume_per_item_m3=0.05)
    assert out.volume_m3 == pytest.approx(0.5)
    assert out.mass_kg == pytest.approx(200.0)


def test_a_missing_quantity_is_not_treated_as_zero():
    assert convert(None, "kg", 1000).missing == "quantity"


def test_an_unknown_unit_is_reported_rather_than_assumed():
    assert convert(10, "schepel", 1000).missing == "unit"


def test_a_negative_quantity_is_refused():
    """A negative quantity would bring a total down and could let a limit be met
    that is not met."""
    assert convert(-5, "kg", 1000).missing == "negative"


# --- Wat mensen intypen ---------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [("liter", "l"), ("LITER", "l"), (" Ltr ", "l"), ("m³", "m3"), ("cbm", "m3"),
     ("kubieke meter", "m3"), ("tonnes", "ton"), ("MT", "ton"), ("stuks", "pcs"),
     ("Stück", "pcs"), ("europallets", "pallet"), ("big bag", "bag")],
)
def test_the_units_people_actually_type_are_understood(text, expected):
    """The old free input has produced years of divergent spellings and those are
    still in stored consignments. Those have to keep working."""
    unit = get_unit(text)
    assert unit is not None and unit.code == expected


def test_an_empty_unit_is_simply_absent():
    assert get_unit("") is None and get_unit(None) is None


# --- Wat de interface voorstelt -------------------------------------------


def test_a_liquid_offers_litres_first_and_bulk_offers_tonnes():
    assert suggested_units("liquid")[0] == "l"
    assert default_unit("bulk_material") == "ton"
    assert default_unit("general_cargo") == "pcs"


def test_wood_is_measured_in_cubic_metres_first():
    assert default_unit("wood") == "m3"


def test_an_unknown_category_still_gets_a_usable_list():
    """Getting stuck on an exception is worse than an unusual unit."""
    assert suggested_units("something_new")
    assert default_unit(None) == "pcs"


def test_every_suggested_unit_exists():
    from app.services.units import SUGGESTED_BY_CATEGORY, UNITS

    for category, codes in SUGGESTED_BY_CATEGORY.items():
        for code in codes:
            assert code in UNITS, f"{category} suggests unknown unit {code}"


# --- The basis of a density -----------------------------------------------


def test_the_density_basis_is_derived_and_named():
    """The goods database does not say whether a figure is a bulk or a material
    density; the category is the only handhold. Making that explicit here is
    better than pretending it is known."""
    assert density_basis("liquid") is DensityBasis.LIQUID
    assert density_basis("bulk_material") is DensityBasis.BULK
    assert density_basis("metal") is DensityBasis.SOLID
    assert density_basis("iets anders") is DensityBasis.UNKNOWN


# --- Weergave -------------------------------------------------------------


def test_a_quantity_is_shown_with_its_symbol():
    assert format_quantity(1200, "l") == "1 200 L"
    assert format_quantity(20.5, "ton") == "20.5 t"
    assert format_quantity(3, "pcs") == "3 st"


def test_a_quantity_without_a_unit_is_just_the_number():
    assert format_quantity(12, None) == "12"
    assert format_quantity(None, "kg") == ""


def test_units_declare_a_dimension():
    assert get_unit("l").dimension is Dimension.VOLUME
    assert get_unit("ton").dimension is Dimension.MASS
    assert get_unit("pallet").dimension is Dimension.COUNT
