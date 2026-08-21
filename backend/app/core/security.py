from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from typing import Any, Mapping

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ALGORITHM = "HS256"
SESSION_PASSWORD_CLAIM = "pwd"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def password_fingerprint(password_hash: str) -> str:
    """Return a one-way session version that changes with the password hash."""
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    password_hash: str | None = None,
    expires_minutes: int | None = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if password_hash:
        payload[SESSION_PASSWORD_CLAIM] = password_fingerprint(password_hash)
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token_claims(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        return None
    return payload


def token_matches_password(claims: Mapping[str, Any], password_hash: str) -> bool:
    """Reject legacy tokens and tokens issued before a password change."""
    supplied = claims.get(SESSION_PASSWORD_CLAIM)
    if not isinstance(supplied, str) or not supplied:
        return False
    expected = password_fingerprint(password_hash)
    return hmac.compare_digest(supplied, expected)


#: Marks a token as "the password was right, the second factor is still to
#: come". A challenge is not a session: it is refused everywhere a session is
#: expected, or the second factor would be a formality anybody could skip by
#: presenting the challenge as a cookie.
CHALLENGE_CLAIM = "two_factor_challenge"

#: Long enough to fetch a phone or a mailbox, short enough that a challenge
#: left on a screen is not a spare key.
CHALLENGE_MINUTES = 10


def create_challenge_token(subject: str, password_hash: str) -> str:
    """A short-lived proof that the password was accepted, and nothing more."""
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=CHALLENGE_MINUTES),
        CHALLENGE_CLAIM: True,
        SESSION_PASSWORD_CLAIM: password_fingerprint(password_hash),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_challenge_token(token: str) -> dict[str, Any] | None:
    """The claims of a challenge token, or ``None`` if this is not one.

    A session token presented here is refused as well: the two are separate
    kinds of proof and swapping one for the other is exactly the mistake this
    check exists to prevent.
    """
    payload = decode_access_token_claims(token)
    if payload is None or not payload.get(CHALLENGE_CLAIM):
        return None
    return payload
