"""Lezen en schrijven van import-templates (xlsx, csv, txt)."""

from __future__ import annotations

import csv
import io

import openpyxl
from openpyxl import Workbook


def build_xlsx_template(headers: list[str], example_row: list[str], sheet_name: str = "Template") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    ws.append(example_row)
    for col in ws.iter_cols(min_row=1, max_row=1):
        for cell in col:
            cell.font = openpyxl.styles.Font(bold=True)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _split_line(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []
    if "\t" in line:
        return [c.strip() for c in line.split("\t")]
    if "|" in line:
        return [c.strip() for c in line.split("|")]
    if ";" in line and line.count(";") >= 1:
        return [c.strip() for c in line.split(";")]
    if "," in line and line.count(",") >= 1:
        return [c.strip() for c in line.split(",")]
    return [line]


def read_tabular_file(content: bytes, filename: str) -> list[list[str]]:
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm")):
        return _read_xlsx(content)
    if name.endswith(".csv"):
        return _read_csv(content)
    return _read_text(content)


def _read_xlsx(content: bytes) -> list[list[str]]:
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        cells = [_cell_str(c) for c in row]
        if any(cells):
            rows.append(cells)
    wb.close()
    return rows


def _cell_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _read_csv(content: bytes) -> list[list[str]]:
    text = _decode_text(content)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.reader(io.StringIO(text), dialect)
    return [[c.strip() for c in row] for row in reader if any(cell.strip() for cell in row)]


def _read_text(content: bytes) -> list[list[str]]:
    text = _decode_text(content)
    rows: list[list[str]] = []
    for line in text.splitlines():
        cells = _split_line(line)
        if cells:
            rows.append(cells)
    return rows


def rows_to_pipe_text(rows: list[list[str]], skip_header: bool = False) -> str:
    start = 1 if skip_header and len(rows) > 1 else 0
    lines: list[str] = []
    for row in rows[start:]:
        while row and not row[-1]:
            row = row[:-1]
        if not any(cell.strip() for cell in row):
            continue
        lines.append(" | ".join(cell.strip() for cell in row))
    return "\n".join(lines)


def normalize_header(value: str) -> str:
    return value.lower().strip().replace(" ", "_")
