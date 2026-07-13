import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.user import User
from app.services.dg.compliance import check_compliance
from app.services.dg.lookup import lookup_un_number

router = APIRouter(prefix="/dg", tags=["dangerous-goods"])


class ComplianceRequest(BaseModel):
    entries: list[dict] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)
    language: str = "nl"

_INSTRUCTIONS_PATH = Path(__file__).resolve().parents[2] / "config" / "dg_instructions.json"


@router.get("/instructions")
def dg_instructions(user: User = Depends(get_current_user)):
    return json.loads(_INSTRUCTIONS_PATH.read_text(encoding="utf-8"))


@router.get("/lookup")
def dg_lookup(un: str = Query(..., min_length=4, max_length=12), user: User = Depends(get_current_user)):
    result = lookup_un_number(un)
    if not result:
        raise HTTPException(status_code=404, detail="UN-nummer niet gevonden in ADR-database")
    return result


@router.post("/compliance")
def dg_compliance(payload: ComplianceRequest, user: User = Depends(get_current_user)):
    if not payload.entries:
        raise HTTPException(status_code=400, detail="entries required")
    return check_compliance(payload.entries, payload.profiles, payload.language)
