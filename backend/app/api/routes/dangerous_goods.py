import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

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
        raise HTTPException(status_code=404, detail="UN-nummer niet gevonden in ADR-database")
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
    """Vul DG-posities automatisch aan en stel de officiële documentregels samen."""
    return prepare_entries(payload.entries, payload.lines, payload.profiles, payload.language)


def _q_check_status(outcome: dict, profiles: list[str], language: str) -> dict | None:
    """Maak zichtbaar of de IATA Q-controle daadwerkelijk is uitgevoerd."""
    if "IATA_DGR" not in {profile.upper() for profile in profiles}:
        return None

    q_values = outcome.get("q_values") or []
    if q_values:
        if any(item.get("status") == "exceeded" for item in q_values):
            status = "exceeded"
        elif any(item.get("status") == "incomplete" for item in q_values):
            status = "incomplete"
        else:
            status = "checked"
    else:
        status = "not_checked"

    messages = {
        "nl": {
            "checked": "De Q-controle is uitgevoerd voor de ingevoerde 'all packed in one'-gegevens.",
            "incomplete": "De Q-controle is niet volledig: vul voor iedere deelnemende stof n en M groter dan nul in.",
            "exceeded": "De berekende Q-waarde is groter dan 1.",
            "not_checked": "Geen Q-controle uitgevoerd. Is 'all packed in one' van toepassing, vul dan per stof de nettohoeveelheid n en de maximaal toegestane hoeveelheid M in.",
        },
        "en": {
            "checked": "The Q check was performed for the entered all-packed-in-one data.",
            "incomplete": "The Q check is incomplete: enter n and M greater than zero for every participating substance.",
            "exceeded": "The calculated Q value exceeds 1.",
            "not_checked": "No Q check was performed. If all packed in one applies, enter net quantity n and maximum permitted quantity M for each substance.",
        },
        "de": {
            "checked": "Die Q-Prüfung wurde für die eingegebenen All-packed-in-one-Daten durchgeführt.",
            "incomplete": "Die Q-Prüfung ist unvollständig: Geben Sie für jeden beteiligten Stoff n und M größer als null ein.",
            "exceeded": "Der berechnete Q-Wert ist größer als 1.",
            "not_checked": "Keine Q-Prüfung durchgeführt. Falls All packed in one zutrifft, geben Sie je Stoff die Nettomenge n und die höchstzulässige Menge M ein.",
        },
    }
    lang = language if language in messages else "en"
    return {"status": status, "message": messages[lang][status]}


def _surface_q_status(outcome: dict, q_status: dict) -> None:
    """Gebruik het bestaande bevindingenpaneel voor een gemiste Q-controle."""
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
    q_status = _q_check_status(outcome, profiles, payload.language)
    if q_status:
        outcome["q_check_status"] = q_status
        _surface_q_status(outcome, q_status)
    return outcome
