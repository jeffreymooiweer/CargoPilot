"""The articles library: the organisation's own codes for what it ships.

An article is "our code X means UN 1263, this proper shipping name, packing
group II, in 25 L steel jerricans". Entered once, so a goods line that names
the code carries its classification into the dangerous goods step without
anybody typing a UN number again. Master data the office reuses, like the
address book, and kept beside the history for the same reason.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: The organisation's own code, unique case-insensitively (enforced in
    #: the service, so "abc-1" and "ABC-1" are one article).
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    #: Four digits, or empty for an article that is not dangerous goods.
    un_number: Mapped[str] = mapped_column(String(8), default="")
    proper_shipping_name: Mapped[str] = mapped_column(String(255), default="")
    technical_name: Mapped[str] = mapped_column(String(255), default="")
    hazard_class: Mapped[str] = mapped_column(String(16), default="")
    packing_group: Mapped[str] = mapped_column(String(8), default="")
    type_of_package: Mapped[str] = mapped_column(String(64), default="")
    #: What one package holds, with its unit: "25 L", "200 kg".
    net_per_package: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator: Mapped[User | None] = relationship()
