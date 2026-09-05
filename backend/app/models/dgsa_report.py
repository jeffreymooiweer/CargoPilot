"""The safety adviser's annual report as kept: one per year and scope.

The counted half is recomputed from the history whenever the report is
opened; what is kept here is the adviser's half — the answers to the
questions the form asks — so a report can be filled in over weeks and be
found again next year. ADR 1.8.3.3 says the report is kept five years.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class DgsaReport(Base):
    __tablename__ = "dgsa_reports"
    __table_args__ = (UniqueConstraint("year", "scope", name="uq_dgsa_reports_year_scope"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    #: Whose shipments the report is over: "" for the whole installation,
    #: "none" for the shipments without a department, or a department id.
    scope: Mapped[str] = mapped_column(String(16), default="")
    answers_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator: Mapped[User | None] = relationship()
