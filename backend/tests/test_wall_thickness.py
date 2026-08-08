"""Een hoekprofiel is geen massieve staaf.

Uit de praktijk gemeld: tien stalen hoekprofielen van 6 m, 80 bij 80, wogen
volgens de applicatie 301,44 kg per stuk. Een L 80x80x8 weegt 9,63 kg per meter,
dus ruim 57 kg voor zes meter. De applicatie zat er een factor vijf naast, en er
stond niets op het scherm dat verried dat er een maat ontbrak.

De oorzaak: de doorsnede was wél herkend — ``detect_product_type`` levert
``angle_profile`` — maar het rekenpad daarvoor eiste vier maten uit de
*omschrijving*. Wie er drie in de kolommen zette viel door naar de generieke tak
en kreeg een massief blok van 600 x 8 x 8 cm.

Wat hier wordt vastgelegd is niet alleen dat de vierde maat nu bestaat, maar dat
zij verplicht is: een vorm met een wand zonder wanddikte levert geen getal op.
Liever geen gewicht dan een gewicht dat vijf keer te hoog is en er even stellig
uitziet.
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


# --- De melding zelf ------------------------------------------------------


def test_an_angle_profile_without_its_thickness_produces_no_weight(db):
    result = line(db, "Staal hoekprofiel | 10 | stuks", **L80)
    assert result["weight_total_kg"] is None
    assert "wall_thickness_missing" in result["messages"]
    assert result["status"] == "needs_review"


def test_it_is_emphatically_not_weighed_as_a_solid_bar(db):
    """De oude uitkomst was 301,44 kg per stuk. Die mag nooit terugkomen."""
    result = line(db, "Staal hoekprofiel | 10 | stuks", **L80)
    solid = 6.0 * 0.08 * 0.08 * STEEL
    assert solid == pytest.approx(301.44)
    assert result["weight_each_kg"] != pytest.approx(solid)


def test_with_the_thickness_it_matches_the_steel_tables(db):
    """L 80x80x8 is 9,63 kg/m volgens de tabellen; de formule negeert de
    afronding in de hoek en komt op 9,55."""
    result = line(db, "Staal hoekprofiel | 10 | stuks", **L80, wall_thickness_m=0.008)
    assert result["weight_each_kg"] == pytest.approx(57.27, abs=0.01)
    assert result["weight_total_kg"] == pytest.approx(572.74, abs=0.1)
    assert result["messages"] == []


def test_the_outer_volume_is_still_known_without_the_thickness(db):
    """Hoeveel staal erin zit is onbekend; hoeveel ruimte het inneemt niet.
    Dat laatste hangt alleen van de buitenmaten af."""
    result = line(db, "Staal hoekprofiel | 10 | stuks", **L80)
    assert result["transport_volume_m3"] == pytest.approx(0.384)


# --- Kokers ---------------------------------------------------------------


@pytest.mark.parametrize("wall,expected", [(0.004, 57.27), (0.005, 70.65)])
def test_a_square_tube_uses_its_wall(db, wall, expected):
    result = line(db, "Koker | 1 | stuks", **L80, wall_thickness_m=wall)
    assert result["weight_each_kg"] == pytest.approx(expected, abs=0.01)


def test_a_tube_without_a_wall_is_refused_too(db):
    assert "wall_thickness_missing" in line(db, "Koker | 1 | stuks", **L80)["messages"]


# --- Waar de wand niet speelt ---------------------------------------------


def test_a_plate_needs_no_wall_thickness(db):
    """Drie maten beschrijven een plaat volledig; er is geen vierde."""
    result = line(db, "Stalen plaat | 10 | stuks", width_m=2.0, height_m=1.0, length_m=0.01)
    assert result["weight_each_kg"] == pytest.approx(157.0)
    assert "wall_thickness_missing" not in result["messages"]


def test_a_wooden_beam_needs_no_wall_thickness(db):
    result = line(db, "Eiken balk | 1 | stuks", width_m=0.2, height_m=0.2, length_m=3.0)
    assert result["weight_each_kg"] == pytest.approx(86.4)
    assert "wall_thickness_missing" not in result["messages"]


def test_only_shapes_with_a_wall_are_in_the_set():
    """Als hier ooit "plate" of "beam" bij komt, verdwijnt bij die goederen het
    gewicht terwijl er niets ontbreekt."""
    assert WALL_PROFILE_TYPES == {"angle_profile", "square_tube", "round_tube"}


# --- Wat er al werkte, blijft werken --------------------------------------


def test_the_description_may_still_carry_all_four(db):
    """Wie "hoekstaal 80x80x8x6000" typt hoeft de kolommen niet in."""
    from_text = line(db, "Hoekstaal 80x80x8x6000 mm | 1 | stuks")
    from_fields = line(db, "Staal hoekprofiel | 1 | stuks", **L80, wall_thickness_m=0.008)
    assert from_text["weight_each_kg"] == pytest.approx(from_fields["weight_each_kg"], rel=0.01)


def test_a_catalogue_profile_needs_no_thickness_at_all(db):
    """Een HEA 200 draagt zijn gewicht per meter in de catalogus; de doorsnede
    hoeft niet te worden nagerekend."""
    result = line(db, "HEA 200 | 1 | stuks", length_m=6.0)
    assert result["weight_total_kg"] is not None
    assert "wall_thickness_missing" not in result["messages"]


def test_a_zero_thickness_counts_as_absent(db):
    """Nul is geen wand. Doorrekenen zou een deling of een negatieve doorsnede
    opleveren, en 0 mm invullen is bijna altijd een half ingevuld veld."""
    result = line(db, "Staal hoekprofiel | 1 | stuks", **L80, wall_thickness_m=0)
    assert "wall_thickness_missing" in result["messages"]


# --- Ronde doorsneden -----------------------------------------------------
#
# Een ronde buis heeft geen hoogte nodig: de breedte is de diameter en de
# wanddikte geeft de binnendiameter. En een massieve ronde staaf werd tot
# v1.37.1 als een balk van d bij d gewogen, want er was voor geen van beide
# vormen een rekenpad — calc_round_bar en calc_round_tube stonden al die tijd
# ongebruikt in de engine.


def test_a_round_tube_needs_only_a_diameter_a_length_and_a_wall(db):
    """108 mm buitendiameter met 4 mm wand is 10,26 kg/m volgens de tabellen."""
    result = line(
        db, "Stalen buis | 1 | stuks",
        width_m=0.108, length_m=6.0, wall_thickness_m=0.004,
    )
    assert result["weight_each_kg"] == pytest.approx(61.56, abs=0.05)
    assert result["messages"] == []


def test_a_round_tube_asks_for_a_height_it_does_not_need(db):
    """Geen hoogte ingevuld, en toch een gewicht: dat is het hele punt."""
    result = line(db, "Stalen buis | 1 | stuks", width_m=0.108, length_m=6.0,
                  wall_thickness_m=0.004)
    assert result["weight_each_kg"] is not None


def test_a_round_bar_is_a_cylinder_and_not_a_block(db):
    """Een staaf van 50 mm over 6 m is 92,48 kg. Als blok van d bij d zou het
    117,75 kg zijn — 4/pi, oftewel 27% te zwaar."""
    result = line(db, "Rond staal | 1 | stuks", width_m=0.05, length_m=6.0)
    assert result["weight_each_kg"] == pytest.approx(92.48, abs=0.05)
    assert result["weight_each_kg"] != pytest.approx(0.05 * 0.05 * 6 * STEEL)


def test_a_round_bar_needs_no_wall_thickness(db):
    result = line(db, "Rond staal | 1 | stuks", width_m=0.05, length_m=6.0)
    assert "wall_thickness_missing" not in result["messages"]


def test_a_wall_thicker_than_the_radius_is_refused(db):
    """Anders levert de binnenstraal een negatief oppervlak op, en een negatief
    gewicht ziet er net zo stellig uit als een positief."""
    result = line(db, "Stalen buis | 1 | stuks", width_m=0.02, length_m=6.0,
                  wall_thickness_m=0.02)
    assert result["weight_each_kg"] is None
    assert "wall_thickness_invalid" in result["messages"]


def test_a_round_tube_without_a_wall_still_asks(db):
    result = line(db, "Stalen buis | 1 | stuks", width_m=0.108, length_m=6.0)
    assert result["weight_each_kg"] is None
    assert "wall_thickness_missing" in result["messages"]


def test_the_outer_box_is_what_gets_stowed(db):
    """Voor de stuwage telt de omhullende doos, niet de cirkel."""
    result = line(db, "Rond staal | 2 | stuks", width_m=0.05, length_m=6.0)
    assert result["transport_volume_m3"] == pytest.approx(0.05 * 0.05 * 6.0 * 2)
