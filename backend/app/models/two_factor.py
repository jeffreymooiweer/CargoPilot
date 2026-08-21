"""What a second factor is made of.

Three tables, because the three things have three lifetimes: the enrolment
lasts until somebody turns it off, a recovery code lasts until it is spent,
and a mailed code lasts five minutes.

None of it lives on the ``users`` table. This application has no migration
runner — ``create_all`` makes missing tables and never adds a column to an
existing one — so a new column there would work on a fresh install and break
every upgrade.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TwoFactorEnrolment(Base):
    """One account's second factor, if it has one."""

    __tablename__ = "two_factor_enrolments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    #: "totp" for an authenticator app, "email" for a code by message.
    method: Mapped[str] = mapped_column(String(16))
    #: The shared secret, base32, for TOTP. Empty for the mail method, which
    #: has nothing to share: every code is made at the moment it is asked for.
    secret: Mapped[str] = mapped_column(String(64), default="")
    #: An enrolment is only real once a first code has been checked. Setting
    #: up TOTP and never scanning the QR would otherwise lock the account.
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())


class TwoFactorRecoveryCode(Base):
    """One of the codes handed out when the second factor is switched on.

    Stored as a hash, like every other credential here: a leaked database
    must not be a set of working keys.
    """

    __tablename__ = "two_factor_recovery_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), index=True)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)


class TwoFactorCode(Base):
    """A code mailed for one sign-in, or for confirming the mail method."""

    __tablename__ = "two_factor_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: Every wrong guess counts. Six digits is a million possibilities, which
    #: is plenty against a person and nothing against a script.
    attempts: Mapped[int] = mapped_column(Integer, default=0)
