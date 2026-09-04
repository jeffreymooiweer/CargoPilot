"""Who is calling.

In the organisation application every call carries a session cookie, and the
account behind it is what the routes receive. In the open application there
are no accounts to carry, so the routes receive a visitor instead: an object
that satisfies the same signature and identifies nobody. The routes that would
need a real account — the settings screen, the equipment library, mail — are
not mounted in that application at all (see ``main.py``), so the visitor only
ever reaches the work: parsing, judging, rendering.
"""
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    CHALLENGE_CLAIM,
    decode_access_token_claims,
    token_matches_password,
)
from app.models.user import User

#: The name the open application's visitor goes by: nobody. Deliberately
#: empty rather than "anonymous", so nothing downstream can mistake it for a
#: user name and print it on a document or in a mail.
VISITOR_USERNAME = ""


def visitor() -> User:
    """The open application's caller.

    A transient model instance, never added to a session: it has no row, no
    id worth anything and no password. Its role is the plainest one, so
    ``require_admin`` refuses it as it would refuse anybody else — a belt for
    the braces of the admin routes not being mounted.
    """
    return User(id=0, username=VISITOR_USERNAME, email="", password_hash="",
                role="user", active=True)


def get_current_user(
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias="access_token"),
) -> User:
    if get_settings().is_open:
        return visitor()
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    claims = decode_access_token_claims(access_token)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if claims.get(CHALLENGE_CLAIM):
        # A half-finished sign-in, presented as a whole one. Without this the
        # second factor would be a formality: anybody could stop at the
        # challenge and use it as a session cookie.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Two-factor verification not finished")
    user = db.query(User).filter(User.username == claims["sub"]).first()
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    if not token_matches_password(claims, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user
