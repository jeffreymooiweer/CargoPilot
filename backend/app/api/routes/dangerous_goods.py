import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.messages import error as api_error
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.dg_compliance import ComplianceRequest
from app.services.dg.autofill import prepare_entries
from app.services.dg.compliance import check_compliance
from app.services.dg.database import get_un_entries, offline_lookup, search_packagings, search_un_numbers
from app.services.dg.enrichment import enrich_un_entry
from app.services.dg.lookup import lookup_un_number
from app.services.dg.naming import proper_shipping_name

router = APIRouter(prefix="/dg", tags=["dangerous-goods"])


class PrepareRequest(BaseModel):
    entries: list[dict] = Field(default_factory=list)
    lines: list[dict] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)
    language: str = "nl"


_INSTRUCTIONS_PATH = Path(__file__).resolve().parents[2] / "config" / "dg_instructions.json"


@router.get("/instructions")
def dg_instructions(user: User = Depends(get_current_user)):
    return json.loads(_INSTRUCTIONS_PATH.read_text(encoding="utf-8"))


@router.get("/lookup")
def dg_lookup(
    un: str = Query(..., min_length=4, max_length=12),
    language: str = Query(default="nl", max_length=10),
    profiles: list[str] = Query(default_factory=list),
    user: User = Depends(get_current_user),
):
    result = lookup_un_number(un) or offline_lookup(un, language, profiles)
    if not result:
        raise api_error(404, "dg.un_number_not_found")
    offline_entries = get_un_entries(un)
    if offline_entries:
        for key, value in enrich_un_entry(offline_entries[0], language).items():
            result.setdefault(key, value)
        result["proper_shipping_name"] = proper_shipping_name(
            offline_entries[0], language, profiles
        )
    return result


@router.get("/search")
def dg_search(
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(default=12, ge=1, le=30),
    language: str = Query(default="nl", max_length=10),
    profiles: list[str] = Query(default_factory=list),
    user: User = Depends(get_current_user),
):
    return {"results": search_un_numbers(q, limit=limit, language=language, profiles=profiles)}


@router.get("/packagings")
def dg_packagings(
    q: str = Query(default="", max_length=80),
    limit: int = Query(default=150, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    return {"results": search_packagings(q, limit=limit)}


@router.post("/prepare")
def dg_prepare(payload: PrepareRequest, user: User = Depends(get_current_user)):
    """Complete DG positions automatically and compose the official document lines."""
    return prepare_entries(payload.entries, payload.lines, payload.profiles, payload.language)


def _surface_q_status(outcome: dict, q_status: dict) -> None:
    """Use the existing findings panel for a Q check that did not run."""
    if q_status["status"] not in {"not_checked", "incomplete"}:
        return
    outcome.setdefault("iata_segregation", []).insert(
        0,
        {
            "rule": "IATA DGR 5.0.2.11 — Q",
            "severity": "warning",
            "message": q_status["message"],
            "products": "All packed in one",
        },
    )


@router.post("/compliance")
def dg_compliance(payload: ComplianceRequest, user: User = Depends(get_current_user)):
    if not payload.entries:
        raise HTTPException(status_code=400, detail="entries required")

    profiles = payload.profile_names()
    outcome = check_compliance(payload.as_dicts(), profiles, payload.language)
    # Since v1.33.0 check_compliance decides for itself whether the Q check ran,
    # so that the export sees it too. All that is left here is showing it in the
    # panel.
    if outcome.get("q_check_status"):
        _surface_q_status(outcome, outcome["q_check_status"])
    return outcome
