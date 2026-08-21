"""Requesting and spending a password reset.

Two rules shape this module.

**The answer to "I forgot my password" is always the same.** Whether the
name exists, whether the account is active, whether it has an address, even
whether the mail server accepted the message — all of it is invisible to
whoever asked. Otherwise the form becomes a way to find out who has an
account here, one guess at a time.

**A token is a password.** Only its hash is stored, it expires, it works
once, and using it invalidates every other outstanding token for that
account — including the one an attacker may have requested moments earlier.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.auth import PasswordResetToken
from app.models.user import User

logger = logging.getLogger(__name__)

#: Long enough to walk to another device and read the mail, short enough
#: that a forwarded message is not a standing key to the account.
TOKEN_TTL_MINUTES = 60


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def find_account(db: Session, identifier: str) -> User | None:
    """The account someone means by a user name or an address.

    Both are accepted because both are what people remember. An inactive
    account resolves to nothing: reactivating is an administrator's decision,
    not something a reset link should quietly do.
    """
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    user = (
        db.query(User)
        .filter((User.username == identifier) | (User.email == identifier))
        .first()
    )
    if user is None or not user.active or not (user.email or "").strip():
        return None
    return user


#: A new colleague may be on holiday when their account is made, and an
#: invitation that expires before they read it costs an administrator a
#: second round. A week is long enough to be useful and short enough that a
#: forgotten mailbox is not a standing door.
INVITE_TTL_MINUTES = 7 * 24 * 60


def issue(db: Session, user: User, ttl_minutes: int = TOKEN_TTL_MINUTES) -> str:
    """Create a token for this account and return it, once.

    Any earlier token is dropped first: a reset that was requested and never
    used should not stay valid beside the new one.
    """
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)

    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=_now() + timedelta(minutes=ttl_minutes),
    ))
    db.commit()
    return token


def redeem(db: Session, token: str) -> User | None:
    """The account this token belongs to, if it may still be used.

    Returns ``None`` for an unknown, expired or spent token — the caller
    tells them all apart with the same sentence, because the difference is
    only useful to somebody guessing.
    """
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_token(token or ""))
        .first()
    )
    if row is None or row.used_at is not None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        # SQLite hands back naive datetimes; they were written in UTC.
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < _now():
        return None
    return db.get(User, row.user_id)


def spend(db: Session, token: str) -> None:
    """Mark the token used, and drop the account's other outstanding ones."""
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_token(token or ""))
        .first()
    )
    if row is None:
        return
    row.used_at = _now()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == row.user_id,
        PasswordResetToken.id != row.id,
        PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)
    db.commit()


def link_for(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/reset-password?token={token}"
