"""What the groupage page and the trips list exchange with the server."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TripConsignmentIn(BaseModel):
    """One consignment as it sits on the vehicle, and where it came from."""

    name: str = Field(default="", max_length=120)
    entries: list[dict[str, Any]] = Field(default_factory=list)
    #: The kept shipment this was picked from, when it was; a file has none.
    shipment_id: int | None = None


class TripIn(BaseModel):
    """A trip as the groupage page hands it over to be kept.

    The server runs the check itself rather than trusting a result the
    browser sends, so the kept judgement is produced by the same code as the
    one on the screen and the two cannot disagree.
    """

    name: str = Field(default="", max_length=120)
    consignments: list[TripConsignmentIn] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)
    language: str = Field(default="nl", max_length=8)
    unit_max_mass_tonnes: float | None = Field(default=None, ge=0, le=200)


class TripSummary(BaseModel):
    id: int
    name: str
    language: str
    regulations: list[str]
    consignment_count: int
    total_points: float | None
    exemption_lost: bool
    unit_max_mass_tonnes: float | None
    created_by: str
    department_id: int | None = None
    department: str = ""
    created_at: datetime
    updated_at: datetime


class TripDetail(TripSummary):
    consignments: list[dict[str, Any]]
    #: The check's answer as it was given when the trip was kept.
    result: dict[str, Any]
    #: The editions the answer was computed against, from the manifest.
    editions: dict[str, Any]


class TripPage(BaseModel):
    items: list[TripSummary]
    total: int
    page: int
    per_page: int
