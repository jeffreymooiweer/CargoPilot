import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.messages import error as api_error
from app.core.deps import get_current_user
from app.core.ratelimit import TRIP_CHECK, limiter
from app.models.user import User
from app.schemas.dg_compliance import ComplianceRequest
from app.services.dg.autofill import prepare_entries
from app.services.dg.compliance import check_compliance
from app.services.dg.database import get_un_entries, offline_lookup, search_packagings, search_un_numbers
from app.services.dg.enrichment import enrich_un_entry
from app.services.dg.lookup import lookup_un_number
from app.services.dg.naming import proper_shipping_name
from app.services.dg.return_shipment import return_shipment
from app.services.dg.trip import check_trip

router = APIRouter(prefix="/dg", tags=["dangerous-goods"])


class ReturnRequest(BaseModel):
    values: dict = Field(default_factory=dict)
    lines: list[dict] = Field(default_factory=list)
    dangerous_goods: list[dict] = Field(default_factory=list)


class PrepareRequest(BaseModel):
    entries: list[dict] = Field(default_factory=list)
    lines: list[dict] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)
    language: str = "nl"


class TripConsignment(BaseModel):
    """One consignment as it sits on the vehicle, named so a warning can point.

    The name is the planner's own — a customer, a reference, a pallet number.
    It is never stored: it lives only in the request and in the answer.
    """

    name: str = Field(default="", max_length=120)
    entries: list[dict] = Field(default_factory=list)


class TripRequest(BaseModel):
    consignments: list[TripConsignment] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)
    language: str = "nl"
    #: ADR 3.4.13 turns on the permitted maximum mass of the transport unit,
    #: which is a property of the vehicle and the one thing about the load the
    #: application cannot derive. Optional: without it the limited-quantities
    #: marking is reported as undecided rather than guessed.
    unit_max_mass_tonnes: float | None = Field(default=None, ge=0, le=200)


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


@router.post("/return")
def dg_return(payload: ReturnRequest, user: User = Depends(get_current_user)):
    """The outward consignment turned round: empty uncleaned, back to the filler.

    The transformation lives in the service rather than in the browser because
    what may *not* be carried over is a regulatory judgement — every quantity
    the outward consignment stated is false on the way back — and that belongs
    where it is tested with the rest of the regulatory code.

    Nothing is stored. The answer is the same shape the wizard already holds,
    and every check then runs on it exactly as on a shipment somebody typed.
    """
    return return_shipment(payload.values, payload.lines, payload.dangerous_goods)


@router.post("/trip")
@limiter.limit(TRIP_CHECK)
def dg_trip(request: Request, payload: TripRequest,
            user: User = Depends(get_current_user)):
    """Several consignments on one vehicle, judged as one load.

    The three rules that cannot be decided per consignment — the 1.1.3.6 points,
    the mixed loading of 7.5.2 and the limited-quantities marking of 3.4.13 —
    run over the union of the entries, because that is what those provisions
    were always measuring.

    Nothing is stored. A trip is a calculation, not an entity: an installation
    without a shipment history keeps nothing about shipments, and a trip that
    landed in the database would break that promise for the sake of a screen.
    It is assembled from the request, judged, and forgotten.
    """
    return check_trip(
        [c.model_dump() for c in payload.consignments],
        payload.profiles,
        payload.language,
        payload.unit_max_mass_tonnes,
    )


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
