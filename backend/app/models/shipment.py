"""A shipment the organisation chose to keep.

Only the organisation application with ``CARGOPILOT_HISTORY=true`` ever writes
a row here; every other installation has this table empty, and the start-up
check in ``services/history.py`` refuses to run an installation that has rows
but no longer has the switch, so a kept shipment is never silently orphaned.

Three documents per row, each for a different reader:

- ``snapshot_json`` is the wizard's own state, opaque to the server. It is
  what "open in the wizard" restores, and only the interface reads it.
- ``bundle_json`` is the document bundle request as the export step sent
  it. It is what "the documents again" re-renders — the same code path as
  the download button, so what comes back is what went out.
- ``export_json`` is the structured shipment export of v1.161.0: the
  documented, versioned record with the derived findings and the editions
  they were computed against. It is what a later reader — a report, a
  groupage picked from the history, an eFTI connector — reads.

The columns beside them are the index: what a list filters and sorts on
without opening a document. They are copied out of the export at save time,
because a page that filters wants real columns.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import Department, User


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(120), default="", index=True)
    modality: Mapped[str] = mapped_column(String(16), default="", index=True)
    language: Mapped[str] = mapped_column(String(8), default="nl")
    #: The regimes, comma-separated: "ADR,IMDG". Small enough to keep flat.
    regulations: Mapped[str] = mapped_column(String(64), default="")
    consignor_name: Mapped[str] = mapped_column(String(255), default="")
    consignee_name: Mapped[str] = mapped_column(String(255), default="")
    goods_count: Mapped[int] = mapped_column(Integer, default=0)
    has_dangerous_goods: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    #: The keeper's department at the moment of keeping: whose work this is.
    #: Copied rather than joined through the user, because somebody moving
    #: departments must not take last year's shipments along.
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    bundle_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_json: Mapped[str] = mapped_column(Text, default="{}")

    creator: Mapped[User | None] = relationship()
    department: Mapped[Department | None] = relationship()
