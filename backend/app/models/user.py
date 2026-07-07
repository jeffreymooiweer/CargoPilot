from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship(back_populates="creator")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="New appendix")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    input_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculated_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    creator: Mapped[User] = relationship(back_populates="jobs")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    density_kg_m3: Mapped[float] = mapped_column()
    density_min_kg_m3: Mapped[float | None] = mapped_column(nullable=True)
    density_max_kg_m3: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str] = mapped_column(String(16), default="kg/m3")
    condition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language_labels_json: Mapped[str] = mapped_column(Text, default="{}")
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_type: Mapped[str] = mapped_column(String(64))
    size_label: Mapped[str] = mapped_column(String(64))
    kg_per_meter: Mapped[float] = mapped_column()
    material: Mapped[str] = mapped_column(String(64), default="steel")
    standard: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReferenceItem(Base):
    __tablename__ = "reference_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64), default="electrical")
    reference_weight_kg: Mapped[float] = mapped_column()
    reference_volume_m3: Mapped[float | None] = mapped_column(nullable=True)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    language_labels_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
