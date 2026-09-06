import asyncio
import io
import zipfile

import pytest
from pydantic import ValidationError

from app.api.routes.import_files import WizardRemapRequest
from app.services.spreadsheet_io import (
    ImportLimitError,
    MAX_IMPORT_COLUMNS,
    _validate_xlsx_archive,
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


def test_a_file_that_is_not_the_spreadsheet_its_name_says_is_refused_readably():
    """Truncated, renamed, damaged: a 500 told the person nothing; the
    message code does."""
    for content in (b"PK\x03\x04 not really an archive", b"just text"):
        with pytest.raises(ImportLimitError) as raised:
            read_tabular_file(content, "broken.xlsx", max_rows=10, max_columns=10, max_cell_chars=100)
        assert raised.value.code == "import.unreadable_file"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as inner:
        inner.writestr("hello.txt", "not a workbook")
    with pytest.raises(ImportLimitError) as raised:
        read_tabular_file(archive.getvalue(), "broken.xlsx", max_rows=10, max_columns=10, max_cell_chars=100)
    assert raised.value.code == "import.unreadable_file"


def test_upload_reader_stops_at_limit_plus_one_byte():
    upload = FakeUpload(b"0123456789")

    with pytest.raises(ImportLimitError) as raised:
        asyncio.run(read_limited_upload(upload, max_bytes=5))
    assert raised.value.code == "import.file_too_large"

    assert upload.requested_size == 6


def test_small_upload_is_returned_unchanged():
    upload = FakeUpload(b"abc")

    assert asyncio.run(read_limited_upload(upload, max_bytes=5)) == b"abc"


def test_csv_row_limit_is_enforced_while_reading():
    with pytest.raises(ImportLimitError) as raised:
        read_tabular_file(b"a;b\nc;d\n", "items.csv", max_rows=1)
    assert raised.value.code == "import.too_many_rows"


def test_column_limit_is_enforced():
    with pytest.raises(ImportLimitError) as raised:
        read_tabular_file(b"a;b;c\n", "items.csv", max_columns=2)
    assert raised.value.code == "import.too_many_columns"
    assert raised.value.params["columns"] == 3


def test_cell_length_limit_is_enforced():
    with pytest.raises(ImportLimitError) as raised:
        read_tabular_file(b"abcdef\n", "items.txt", max_cell_chars=5)
    assert raised.value.code == "import.cell_too_long"


def test_xlsx_row_limit_is_enforced_in_read_only_iteration():
    content = build_xlsx_template(["header"], ["value"])

    with pytest.raises(ImportLimitError) as raised:
        read_tabular_file(content, "items.xlsx", max_rows=1)
    assert raised.value.code == "import.too_many_rows"


def test_xlsx_archive_expansion_is_bounded_before_openpyxl_reads_it():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", "x" * 100)

    with pytest.raises(ImportLimitError) as raised:
        _validate_xlsx_archive(buffer.getvalue(), max_uncompressed_bytes=50)
    assert raised.value.code == "import.unpacked_too_large"


def test_remap_payload_rejects_excessive_columns_before_processing():
    with pytest.raises(ValidationError, match="columns"):
        WizardRemapRequest(
            rows=[["x"] * (MAX_IMPORT_COLUMNS + 1)],
            mapping={"description": 0},
        )


def test_explicit_row_validation_accepts_normal_data():
    rows = [["description", "quantity"], ["beam", "2"]]

    validate_tabular_rows(rows)
