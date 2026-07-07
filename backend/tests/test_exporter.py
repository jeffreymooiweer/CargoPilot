import pytest
from app.services.exporter.appendix_exporter import sanitize_cell_value


def test_sanitize_formula_injection():
    assert sanitize_cell_value("=1+1") == "'=1+1"
    assert sanitize_cell_value("+cmd") == "'+cmd"
    assert sanitize_cell_value("normal text") == "normal text"
