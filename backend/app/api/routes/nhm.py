"""The NHM goods nomenclature, searched for box 24 of the CIM."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user
from app.models.user import User
from app.services.nhm import nhm_count, nhm_entry, search_nhm

router = APIRouter(prefix="/nhm", tags=["nhm"])


@router.get("")
def nhm_search(
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(default=10, ge=1, le=25),
    user: User = Depends(get_current_user),
):
    return {"results": search_nhm(q, limit=limit), "count": nhm_count()}


@router.get("/{code}")
def nhm_lookup(code: str, user: User = Depends(get_current_user)):
    entry = nhm_entry(code)
    if entry is None:
        raise HTTPException(status_code=404, detail="Unknown NHM code")
    return entry
