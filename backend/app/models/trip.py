"""A groupage trip the organisation chose to keep.

The judgement over a whole load — several consignments on one vehicle,
assessed together under ADR 1.1.3.6, 7.5.2 and 3.4.13/3.4.14 — used to live
only on the screen that asked for it. An installation that keeps its
shipments (``CARGOPILOT_HISTORY=true``) may keep the trip as well: what was
on the vehicle, the vehicle's permitted maximum mass, and what the check said
at the time, with the editions it said it under. Every other installation has
this table empty, and the start-up check in ``services/history.py`` refuses
to run with rows the switch no longer covers, exactly as for shipments.

Two documents per row. ``consignments_json`` is the load as the planner
assembled it — each consignment's name, its dangerous goods entries and,
when it was picked from the history, the kept shipment it came from.
``result_json`` is the check's answer as it was given, so that reopening the
trip shows what the planner saw rather than what today's rules would say;
the editions are kept beside it so a later reader can tell the two apart.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import Department, User


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: The planner's own name for the load: a vehicle, a route, a date.
    name: Mapped[str] = mapped_column(String(120), default="", index=True)
    language: Mapped[str] = mapped_column(String(8), default="nl")
    #: The regimes, comma-separated, as on a shipment.
    regulations: Mapped[str] = mapped_column(String(64), default="")
    consignment_count: Mapped[int] = mapped_column(Integer, default=0)
    #: The 1.1.3.6 total over the whole load, when the check could settle it.
    total_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: The headline finding: every consignment exempt, the vehicle not.
    exemption_lost: Mapped[bool] = mapped_column(Boolean, default=False)
    unit_max_mass_tonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    #: The keeper's department at the moment of keeping, as on a shipment.
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    consignments_json: Mapped[str] = mapped_column(Text, default="[]")
    result_json: Mapped[str] = mapped_column(Text, default="{}")

    creator: Mapped[User | None] = relationship()
    department: Mapped[Department | None] = relationship()
