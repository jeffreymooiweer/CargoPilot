import pytest
from app.services.parser.dimension_extractor import extract_dimensions, meters_to_cm


@pytest.mark.parametrize(
    "text,expected_mm",
    [
        ("80x80x8x6000", [80, 80, 8, 6000]),
        ("80 x 80 x 8 x 6000", [80, 80, 8, 6000]),
        ("60x60x6x6000mm", [60, 60, 6, 6000]),
        ("50x50x5x6000 mm", [50, 50, 5, 6000]),
    ],
)
def test_dimension_patterns(text, expected_mm):
    dims = extract_dimensions(text)
    assert len(dims.values_m) == 4
    for actual, expected in zip(dims.values_m, expected_mm):
        assert abs(actual * 1000 - expected) < 0.1


def test_unp_length():
    dims = extract_dimensions("UNP 220 mml=5700mm gegalvaniseerd")
    assert dims.profile_size == "UNP 220"
    assert dims.length_m is not None
    assert abs(dims.length_m - 5.7) < 0.01


def test_meters_to_cm():
    assert meters_to_cm(6.0) == 600.0
