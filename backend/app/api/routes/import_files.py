from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models.user import User
from app.services.spreadsheet_io import build_xlsx_template, read_tabular_file
from app.services.wizard_import import WIZARD_EXAMPLE, WIZARD_HEADERS, spreadsheet_to_wizard_text

router = APIRouter(tags=["import"])


class WizardFileParseResult(BaseModel):
    text: str
    has_header: bool


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
    return WizardFileParseResult(text=text, has_header=has_header)
