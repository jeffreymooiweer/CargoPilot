from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    CHALLENGE_CLAIM,
    decode_access_token_claims,
    token_matches_password,
)
from app.models.user import User


def get_current_user(
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias="access_token"),
) -> User:
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
