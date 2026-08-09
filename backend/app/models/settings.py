"""Where preferences live: one row per user, one row for the instance.

Both tables store a single JSON document rather than a column per setting, and
that is deliberate. This application has no migration runner — ``init_app``
calls ``Base.metadata.create_all``, which creates *missing tables* but never
adds a column to a table that already exists. A column-per-setting schema would
therefore work on a fresh install and silently break every upgrade: the new
column exists in the model, not in the database on disk, and every query fails.

With a JSON payload the schema never changes again. Adding a preference means
adding a field to the Pydantic model in ``app.schemas.settings``; databases
written by an older version simply lack the key and fall back to its default.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPreference(Base):
    """The settings one user chose for themselves."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InstanceSetting(Base):
    """The settings that apply to the whole installation. At most one row."""

    __tablename__ = "instance_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
