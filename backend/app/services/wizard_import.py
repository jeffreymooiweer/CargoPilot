"""Wizard-import: spreadsheet naar plaktekst."""

from __future__ import annotations

from app.services.parser.paste_parser import detect_columns
from app.services.spreadsheet_io import rows_to_pipe_text

WIZARD_HEADERS = ["description", "quantity", "unit"]
WIZARD_EXAMPLE = ["staal hoekprofiel 80x80x8x6000", "8", "stuks"]


def spreadsheet_to_wizard_text(rows: list[list[str]]) -> tuple[str, bool]:
    if not rows:
        return "", False
    header_map = detect_columns([c.lower().strip() for c in rows[0]])
    has_header = header_map["description"] is not None or header_map["quantity"] is not None
    return rows_to_pipe_text(rows, skip_header=has_header), has_header
