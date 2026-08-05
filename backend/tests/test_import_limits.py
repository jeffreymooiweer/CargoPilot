import asyncio

import pytest
from pydantic import ValidationError

from app.api.routes.import_files import WizardRemapRequest
from app.services.spreadsheet_io import (
    ImportLimitError,
    MAX_IMPORT_COLUMNS,
    build_xlsx_template,
    read_limited_upload,
    read_tabular_file,
    validate_tabular_rows,
)


class FakeUpload:
    def __init__(self, content: bytes):
        self.content = content
        self.requested_size: int | None = None

    async def read(self, size: int) -> bytes:
        self.requested_size = size
        return self.content[:size]


def test_upload_reader_stops_at_limit_plus_one_byte():
    upload = FakeUpload(b"0123456789")

    with pytest.raises(ImportLimitError, match="groter dan"):
        asyncio.run(read_limited_upload(upload, max_bytes=5))

    assert upload.requested_size == 6


def test_small_upload_is_returned_unchanged():
    upload = FakeUpload(b"abc")

    assert asyncio.run(read_limited_upload(upload, max_bytes=5)) == b"abc"


def test_csv_row_limit_is_enforced_while_reading():
    with pytest.raises(ImportLimitError, match="meer dan 1 rijen"):
        read_tabular_file(b"a;b\nc;d\n", "items.csv", max_rows=1)


def test_column_limit_is_enforced():
    with pytest.raises(ImportLimitError, match="3 kolommen"):
        read_tabular_file(b"a;b;c\n", "items.csv", max_columns=2)


def test_cell_length_limit_is_enforced():
    with pytest.raises(ImportLimitError, match="meer dan 5 tekens"):
        read_tabular_file(b"abcdef\n", "items.txt", max_cell_chars=5)


def test_xlsx_row_limit_is_enforced_in_read_only_iteration():
    content = build_xlsx_template(["header"], ["value"])

    with pytest.raises(ImportLimitError, match="meer dan 1 rijen"):
        read_tabular_file(content, "items.xlsx", max_rows=1)


def test_remap_payload_rejects_excessive_columns_before_processing():
    with pytest.raises(ValidationError, match="kolommen"):
        WizardRemapRequest(
            rows=[["x"] * (MAX_IMPORT_COLUMNS + 1)],
            mapping={"description": 0},
        )


def test_explicit_row_validation_accepts_normal_data():
    rows = [["description", "quantity"], ["beam", "2"]]

    validate_tabular_rows(rows)
