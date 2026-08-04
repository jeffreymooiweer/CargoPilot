"""Regression tests for bounded file and JSON imports."""
import io
import zipfile

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

from app.api.routes.import_files import WizardRemapRequest
from app.services.import_limits import (
    ImportLimitError,
    UploadTooLarge,
    read_upload_limited,
    validate_tabular_rows,
)
from app.services.spreadsheet_io import _validate_xlsx_archive, read_tabular_file


@pytest.mark.asyncio
async def test_upload_reader_stops_at_the_byte_limit():
    upload = UploadFile(io.BytesIO(b"abcdef"), filename="large.csv")

    with pytest.raises(UploadTooLarge):
        await read_upload_limited(upload, max_bytes=5, chunk_bytes=2)


@pytest.mark.asyncio
async def test_upload_reader_accepts_content_at_the_exact_limit():
    upload = UploadFile(io.BytesIO(b"abcde"), filename="ok.csv")

    content = await read_upload_limited(upload, max_bytes=5, chunk_bytes=2)

    assert content == b"abcde"


def test_row_limit_is_enforced():
    with pytest.raises(ImportLimitError, match="meer dan 2 rijen"):
        validate_tabular_rows([["a"], ["b"], ["c"]], max_rows=2)


def test_column_limit_is_enforced():
    with pytest.raises(ImportLimitError, match="meer dan 2 kolommen"):
        validate_tabular_rows([["a", "b", "c"]], max_columns=2)


def test_cell_size_limit_is_enforced():
    with pytest.raises(ImportLimitError, match="meer dan 3 tekens"):
        validate_tabular_rows([["abcd"]], max_cell_chars=3)


def test_csv_reader_rejects_more_than_one_hundred_columns():
    content = (";".join(f"c{i}" for i in range(101)) + "\n").encode()

    with pytest.raises(ImportLimitError, match="meer dan 100 kolommen"):
        read_tabular_file(content, "wide.csv")


def test_remap_request_rejects_oversized_nested_rows():
    with pytest.raises(ValidationError):
        WizardRemapRequest(
            rows=[[str(index) for index in range(101)]],
            mapping={"description": 0},
        )


def test_xlsx_archive_expansion_is_bounded():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", "x" * 100)

    with pytest.raises(ImportLimitError, match="Uitgepakte spreadsheet"):
        _validate_xlsx_archive(buffer.getvalue(), max_uncompressed_bytes=50)
