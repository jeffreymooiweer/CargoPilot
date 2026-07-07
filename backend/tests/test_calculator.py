import pytest
from app.services.calculator.engine import calc_angle_profile, calc_hollow_rect, STEEL_DENSITY


def test_angle_profile_weight():
    _, weight = calc_angle_profile(0.08, 0.08, 0.008, 6.0, STEEL_DENSITY)
    assert abs(weight - 57.2) < 2


def test_hollow_rect_invalid_wall():
    with pytest.raises(ValueError):
        calc_hollow_rect(0.04, 0.04, 0.03, 6.0, STEEL_DENSITY)
