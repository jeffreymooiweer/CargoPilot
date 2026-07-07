import pytest
from app.services.parser.paste_parser import parse_paste


def test_pipe_separated():
    text = "Stalen hoekprofiel 80x80x8x6000 | 8 | stuks"
    rows, mapping = parse_paste(text)
    assert len(rows) == 1
    assert rows[0].quantity == 8
    assert "hoekprofiel" in rows[0].description.lower()


def test_tsv():
    text = "description\tquantity\tunit\nStaal koker 60x60x6x6000\t32\tstuks"
    rows, mapping = parse_paste(text, has_header=True)
    assert len(rows) == 1
    assert rows[0].quantity == 32
