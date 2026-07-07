import pytest

from app.services.dg.detector import apply_un_detection, default_appendix_flags, detect_un_numbers


def test_detect_un_number_variants():
    assert detect_un_numbers("Brandstof UN 1203 in jerrycans") == ["1203"]
    assert detect_un_numbers("ID 8000 compressed gas") == ["8000"]
    assert detect_un_numbers("UN1203 zonder spatie") == ["1203"]


def test_apply_un_detection_sets_dangerous_goods():
    flags = default_appendix_flags()
    flags, messages = apply_un_detection("UN 1993 brandbare vloeistof", flags)
    assert flags["dangerous_goods"] == "Y"
    assert "dg_un_detected" in messages
