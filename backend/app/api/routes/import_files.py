from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from app.core.messages import error as api_error
from app.core.deps import get_current_user
from app.models.user import User
from app.services.spreadsheet_io import (
    ImportLimitError,
    MAX_IMPORT_CELL_CHARS,
    MAX_IMPORT_COLUMNS,
    MAX_IMPORT_ROWS,
    build_xlsx_template,
    read_limited_upload,
    read_tabular_file,
    validate_tabular_rows,
)
from app.services.wizard_import import (
    WIZARD_EXAMPLE,
    WIZARD_HEADERS,
    analyse,
    apply_mapping,
    spreadsheet_to_wizard_text,
)

router = APIRouter(tags=["import"])


class ImportColumn(BaseModel):
    index: int
    header: str
    samples: list[str] = Field(default_factory=list)


class ImportAnalysis(BaseModel):
    columns: list[ImportColumn] = Field(default_factory=list)
    mapping: dict[str, int | None] = Field(default_factory=dict)
    # "header" — the heading row was recognised. "position" — it was guessed
    # from the order, and the interface should let that be adjusted.
    source: str = "none"
    has_header: bool = False


class WizardFileParseResult(BaseModel):
    text: str
    has_header: bool
    analysis: ImportAnalysis = Field(default_factory=ImportAnalysis)
    # The rows travel back so the interface can apply a different mapping
    # without sending the file again. Nothing of it stays on the server.
    rows: list[list[str]] = Field(default_factory=list)


class WizardRemapRequest(BaseModel):
    rows: list[list[str]] = Field(default_factory=list)
    mapping: dict[str, int | None] = Field(default_factory=dict)
    has_header: bool = False

    @field_validator("rows")
    @classmethod
    def _bounded_rows(cls, rows: list[list[str]]) -> list[list[str]]:
        validate_tabular_rows(rows)
        return rows


@router.get("/import/wizard-template")
def download_wizard_template(user: User = Depends(get_current_user)):
    content = build_xlsx_template(WIZARD_HEADERS, WIZARD_EXAMPLE, sheet_name="Wizard import")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="wizard_import_template.xlsx"'},
    )


@router.post("/import/wizard-file", response_model=WizardFileParseResult)
async def parse_wizard_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if not file.filename:
        raise api_error(400, "import.filename_missing")
    try:
        content = await read_limited_upload(file)
    except ImportLimitError as exc:
        raise api_error(413, exc.code, **exc.params) from exc
    if not content:
        raise api_error(400, "import.empty_file")
    try:
        rows = read_tabular_file(
            content,
            file.filename,
            max_rows=MAX_IMPORT_ROWS,
            max_columns=MAX_IMPORT_COLUMNS,
            max_cell_chars=MAX_IMPORT_CELL_CHARS,
        )
    except ImportLimitError as exc:
        raise api_error(422, exc.code, **exc.params) from exc
    text, has_header = spreadsheet_to_wizard_text(rows)
    if not text.strip():
        raise api_error(400, "import.no_usable_lines")
    return WizardFileParseResult(
        text=text,
        has_header=has_header,
        analysis=ImportAnalysis(**analyse(rows).as_dict()),
        rows=rows,
    )


@router.post("/import/wizard-remap", response_model=WizardFileParseResult)
def remap_wizard_rows(
    payload: WizardRemapRequest,
    user: User = Depends(get_current_user),
):
    """The same rows, a different column mapping.

    Separate from the upload because the server keeps nothing of the file: the
    rows travel with the request. That costs some bandwidth and buys the
    guarantee that half a shipment never stays behind on the server.
    """
    if not payload.rows:
        raise api_error(400, "import.no_rows_to_map")
    if payload.mapping.get("description") is None:
        raise api_error(422, "import.description_column_required")
    text = apply_mapping(payload.rows, payload.mapping, payload.has_header)
    if not text.strip():
        raise api_error(400, "import.no_usable_lines")
    return WizardFileParseResult(
        text=text,
        has_header=payload.has_header,
        analysis=ImportAnalysis(
            **{**analyse(payload.rows).as_dict(), "mapping": payload.mapping,
               "source": "user", "has_header": payload.has_header}
        ),
        rows=payload.rows,
    )
