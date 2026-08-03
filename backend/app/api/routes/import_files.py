from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.user import User
from app.services.spreadsheet_io import build_xlsx_template, read_tabular_file
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
    # "header" — de koptekst is herkend. "position" — er is op volgorde geraden
    # en de interface hoort dat te laten bijstellen.
    source: str = "none"
    has_header: bool = False


class WizardFileParseResult(BaseModel):
    text: str
    has_header: bool
    analysis: ImportAnalysis = Field(default_factory=ImportAnalysis)
    # De rijen gaan mee terug zodat de interface een andere indeling kan laten
    # toepassen zonder het bestand nog eens te sturen. Er blijft niets van op
    # de server staan.
    rows: list[list[str]] = Field(default_factory=list)


class WizardRemapRequest(BaseModel):
    rows: list[list[str]] = Field(default_factory=list)
    mapping: dict[str, int | None] = Field(default_factory=dict)
    has_header: bool = False


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
        raise HTTPException(status_code=400, detail="Bestandsnaam ontbreekt")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Leeg bestand")
    rows = read_tabular_file(content, file.filename)
    text, has_header = spreadsheet_to_wizard_text(rows)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Geen importeerbare regels gevonden")
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
    """Dezelfde rijen, een andere kolomindeling.

    Staat los van het uploaden omdat de server niets van het bestand bewaart:
    de rijen reizen mee met het verzoek. Dat kost wat bandbreedte en levert op
    dat er nooit een halve zending op de server blijft liggen.
    """
    if not payload.rows:
        raise HTTPException(status_code=400, detail="Geen regels om in te delen")
    if payload.mapping.get("description") is None:
        raise HTTPException(
            status_code=422,
            detail="Zonder omschrijvingskolom valt er niets te herkennen",
        )
    text = apply_mapping(payload.rows, payload.mapping, payload.has_header)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Geen importeerbare regels gevonden")
    return WizardFileParseResult(
        text=text,
        has_header=payload.has_header,
        analysis=ImportAnalysis(
            **{**analyse(payload.rows).as_dict(), "mapping": payload.mapping,
               "source": "user", "has_header": payload.has_header}
        ),
        rows=payload.rows,
    )
