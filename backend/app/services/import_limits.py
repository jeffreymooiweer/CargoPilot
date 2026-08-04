"""Resource limits for spreadsheet and text imports.

Uploads are user-controlled input. Reading an entire file or accepting an
unbounded nested JSON array lets one authenticated request consume most of the
container memory. These limits are deliberately generous for CargoPilot's use
case while keeping processing bounded.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_XLSX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_IMPORT_ROWS = 20_000
MAX_IMPORT_COLUMNS = 100
MAX_CELL_CHARS = 10_000
UPLOAD_CHUNK_BYTES = 1024 * 1024


class ImportLimitError(ValueError):
    """Base error for a structurally oversized import."""


class UploadTooLarge(ImportLimitError):
    """The raw uploaded file exceeds the byte limit."""


async def read_upload_limited(
    file: UploadFile,
    max_bytes: int = MAX_UPLOAD_BYTES,
    chunk_bytes: int = UPLOAD_CHUNK_BYTES,
) -> bytes:
    """Read an UploadFile without ever accepting more than ``max_bytes``."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(chunk_bytes)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            limit_mb = max_bytes / (1024 * 1024)
            raise UploadTooLarge(f"Bestand is groter dan {limit_mb:g} MB")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_tabular_rows(
    rows: Sequence[Sequence[object]] | Iterable[Sequence[object]],
    *,
    max_rows: int = MAX_IMPORT_ROWS,
    max_columns: int = MAX_IMPORT_COLUMNS,
    max_cell_chars: int = MAX_CELL_CHARS,
) -> None:
    """Validate row, column and cell-size limits.

    Works for already materialised JSON rows as well as rows produced while a
    CSV/XLSX file is being read.
    """
    for row_index, row in enumerate(rows, start=1):
        if row_index > max_rows:
            raise ImportLimitError(f"Import bevat meer dan {max_rows} rijen")
        if len(row) > max_columns:
            raise ImportLimitError(
                f"Rij {row_index} bevat meer dan {max_columns} kolommen"
            )
        for column_index, cell in enumerate(row, start=1):
            if len(str(cell or "")) > max_cell_chars:
                raise ImportLimitError(
                    f"Cel {row_index}:{column_index} bevat meer dan "
                    f"{max_cell_chars} tekens"
                )


def append_validated_row(
    rows: list[list[str]],
    row: list[str],
    *,
    max_rows: int = MAX_IMPORT_ROWS,
    max_columns: int = MAX_IMPORT_COLUMNS,
    max_cell_chars: int = MAX_CELL_CHARS,
) -> None:
    """Append one parsed row while enforcing limits before accumulation."""
    next_index = len(rows) + 1
    if next_index > max_rows:
        raise ImportLimitError(f"Import bevat meer dan {max_rows} rijen")
    if len(row) > max_columns:
        raise ImportLimitError(
            f"Rij {next_index} bevat meer dan {max_columns} kolommen"
        )
    for column_index, cell in enumerate(row, start=1):
        if len(cell) > max_cell_chars:
            raise ImportLimitError(
                f"Cel {next_index}:{column_index} bevat meer dan "
                f"{max_cell_chars} tekens"
            )
    rows.append(row)
