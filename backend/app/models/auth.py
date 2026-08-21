"""Short-lived proof that someone can read a mailbox.

A reset token is a password in disguise: whoever holds it can take over the
account it belongs to. So it is treated like one — the database stores only
a hash, the token itself exists in the mail and nowhere else, it expires,
and it works once.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PasswordResetToken(Base):
    """One outstanding reset for one account."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    #: SHA-256 of the token that went out. A database that leaks must not
    #: hand out working reset links.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    #: Set the moment the token is spent, so a link that is forwarded, logged
    #: by a mail scanner or left in a browser history cannot be used twice.
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
