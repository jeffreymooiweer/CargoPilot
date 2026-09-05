"""The address book: the same five customers, entered once.

A party is a party — the consignee of Monday's shipment is the consignor of
Thursday's — so an entry has no kind, only a name, an address and a contact,
and the details step offers every entry for every party field. Kept only
with the shipment history, like every other thing an organisation keeps
beyond its accounts; an installation without the history has no address
book and no route for one.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str] = mapped_column(Text, default="")
    contact: Mapped[str] = mapped_column(String(255), default="")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
