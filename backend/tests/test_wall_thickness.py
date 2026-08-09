"""An angle profile is not a solid bar.

Reported from practice: ten steel angles of 6 m, 80 by 80, weighed 301.44 kg each
according to the application. An L 80x80x8 weighs 9.63 kg per metre, so a little
over 57 kg for six metres. The application was out by a factor of five, and there
was nothing on the screen betraying that a measurement was missing.

The cause: the cross-section *was* recognised — ``detect_product_type`` returns
``angle_profile`` — but the calculation path for it demanded four measurements
from the *description*. Anyone putting three in the columns fell through to the
generic branch and got a solid block of 600 x 8 x 8 cm.

What is recorded here is not only that the fourth measurement now exists, but
that it is mandatory: a shape with a wall and no wall thickness yields no figure.
Better no weight than a weight five times too high that looks just as confident.
"""

import pytest

from app.core.database import SessionLocal
from app.services.pipeline import WALL_PROFILE_TYPES, parse_and_calculate

STEEL = 7850.0


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def line(db, text: str, **overrides) -> dict:
    payload = {"line_id": 1, **overrides}
    return parse_and_calculate(text, db=db, line_overrides=[payload])["lines"][0]


L80 = {"width_m": 0.08, "height_m": 0.08, "length_m": 6.0}


# --- The message itself ---------------------------------------------------


def test_an_angle_profile_without_its_thickness_produces_no_weight(db):
    result = line(db, "Staal hoekprofiel | 10 | stuks", **L80)
    assert result["weight_total_kg"] is None
    assert "wall_thickness_missing" in result["messages"]
    assert result["status"] == "needs_review"


def test_it_is_emphatically_not_weighed_as_a_solid_bar(db):
    """The old outcome was 301.44 kg each. That must never come back."""
    result = line(db, "Staal hoekprofiel | 10 | stuks", **L80)
    solid = 6.0 * 0.08 * 0.08 * STEEL
    assert solid == pytest.approx(301.44)
    assert result["weight_each_kg"] != pytest.approx(solid)


def test_with_the_thickness_it_matches_the_steel_tables(db):
    """L 80x80x8 is 9.63 kg/m according to the tables; the formula ignores the
    rounding in the corner and arrives at 9.55."""
    result = line(db, "Staal hoekprofiel | 10 | stuks", **L80, wall_thickness_m=0.008)
    assert result["weight_each_kg"] == pytest.approx(57.27, abs=0.01)
    assert result["weight_total_kg"] == pytest.approx(572.74, abs=0.1)
    assert result["messages"] == []


def test_the_outer_volume_is_still_known_without_the_thickness(db):
    """How much steel is in it is unknown; how much space it takes is not. The
    latter depends only on the outside measurements."""
    result = line(db, "Staal hoekprofiel | 10 | stuks", **L80)
    assert result["transport_volume_m3"] == pytest.approx(0.384)


# --- Kokers ---------------------------------------------------------------


@pytest.mark.parametrize("wall,expected", [(0.004, 57.27), (0.005, 70.65)])
def test_a_square_tube_uses_its_wall(db, wall, expected):
    result = line(db, "Koker | 1 | stuks", **L80, wall_thickness_m=wall)
    assert result["weight_each_kg"] == pytest.approx(expected, abs=0.01)


def test_a_tube_without_a_wall_is_refused_too(db):
    assert "wall_thickness_missing" in line(db, "Koker | 1 | stuks", **L80)["messages"]


# --- Where the wall does not come into play -------------------------------


def test_a_plate_needs_no_wall_thickness(db):
    """Three measurements describe a plate completely; there is no fourth."""
    result = line(db, "Stalen plaat | 10 | stuks", width_m=2.0, height_m=1.0, length_m=0.01)
    assert result["weight_each_kg"] == pytest.approx(157.0)
    assert "wall_thickness_missing" not in result["messages"]


def test_a_wooden_beam_needs_no_wall_thickness(db):
    result = line(db, "Eiken balk | 1 | stuks", width_m=0.2, height_m=0.2, length_m=3.0)
    assert result["weight_each_kg"] == pytest.approx(86.4)
    assert "wall_thickness_missing" not in result["messages"]


def test_only_shapes_with_a_wall_are_in_the_set():
    """If "plate" or "beam" is ever added here, the weight disappears for those
    commodities while nothing is missing."""
    assert WALL_PROFILE_TYPES == {"angle_profile", "square_tube", "round_tube"}


# --- What already worked keeps working ------------------------------------


def test_the_description_may_still_carry_all_four(db):
    """Whoever types "hoekstaal 80x80x8x6000" does not need the columns."""
    from_text = line(db, "Hoekstaal 80x80x8x6000 mm | 1 | stuks")
    from_fields = line(db, "Staal hoekprofiel | 1 | stuks", **L80, wall_thickness_m=0.008)
    assert from_text["weight_each_kg"] == pytest.approx(from_fields["weight_each_kg"], rel=0.01)


def test_a_catalogue_profile_needs_no_thickness_at_all(db):
    """An HEA 200 carries its weight per metre in the catalogue; the
    cross-section does not have to be recalculated."""
    result = line(db, "HEA 200 | 1 | stuks", length_m=6.0)
    assert result["weight_total_kg"] is not None
    assert "wall_thickness_missing" not in result["messages"]


def test_a_zero_thickness_counts_as_absent(db):
    """Zero is not a wall. Computing on would produce a division or a negative
    cross-section, and filling in 0 mm is nearly always a half-filled field."""
    result = line(db, "Staal hoekprofiel | 1 | stuks", **L80, wall_thickness_m=0)
    assert "wall_thickness_missing" in result["messages"]


# --- Round cross-sections -------------------------------------------------
#
# A round tube needs no height: the width is the diameter and the wall thickness
# gives the inside diameter. And until v1.37.1 a solid round bar was weighed as a
# beam of d by d, because there was no calculation path for either shape —
# calc_round_bar and calc_round_tube sat unused in the engine all that time.


def test_a_round_tube_needs_only_a_diameter_a_length_and_a_wall(db):
    """108 mm outside diameter with a 4 mm wall is 10.26 kg/m per the tables."""
    result = line(
        db, "Stalen buis | 1 | stuks",
        width_m=0.108, length_m=6.0, wall_thickness_m=0.004,
    )
    assert result["weight_each_kg"] == pytest.approx(61.56, abs=0.05)
    assert result["messages"] == []


def test_a_round_tube_asks_for_a_height_it_does_not_need(db):
    """No height filled in, and a weight all the same: that is the whole point."""
    result = line(db, "Stalen buis | 1 | stuks", width_m=0.108, length_m=6.0,
                  wall_thickness_m=0.004)
    assert result["weight_each_kg"] is not None


def test_a_round_bar_is_a_cylinder_and_not_a_block(db):
    """A bar of 50 mm over 6 m is 92.48 kg. As a block of d by d it would be
    117.75 kg — 4/pi, that is 27% too heavy."""
    result = line(db, "Rond staal | 1 | stuks", width_m=0.05, length_m=6.0)
    assert result["weight_each_kg"] == pytest.approx(92.48, abs=0.05)
    assert result["weight_each_kg"] != pytest.approx(0.05 * 0.05 * 6 * STEEL)


def test_a_round_bar_needs_no_wall_thickness(db):
    result = line(db, "Rond staal | 1 | stuks", width_m=0.05, length_m=6.0)
    assert "wall_thickness_missing" not in result["messages"]


def test_a_wall_thicker_than_the_radius_is_refused(db):
    """Otherwise the inner radius yields a negative area, and a negative weight
    looks just as confident as a positive one."""
    result = line(db, "Stalen buis | 1 | stuks", width_m=0.02, length_m=6.0,
                  wall_thickness_m=0.02)
    assert result["weight_each_kg"] is None
    assert "wall_thickness_invalid" in result["messages"]


def test_a_round_tube_without_a_wall_still_asks(db):
    result = line(db, "Stalen buis | 1 | stuks", width_m=0.108, length_m=6.0)
    assert result["weight_each_kg"] is None
    assert "wall_thickness_missing" in result["messages"]


def test_the_outer_box_is_what_gets_stowed(db):
    """For stowage the enclosing box counts, not the circle."""
    result = line(db, "Rond staal | 2 | stuks", width_m=0.05, length_m=6.0)
    assert result["transport_volume_m3"] == pytest.approx(0.05 * 0.05 * 6.0 * 2)
