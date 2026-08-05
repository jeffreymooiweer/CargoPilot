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


def decode_access_token(token: str) -> str | None:
    """Compatibility helper for callers that only need the subject."""
    payload = decode_access_token_claims(token)
    return str(payload["sub"]) if payload else None


def token_matches_password(claims: Mapping[str, Any], password_hash: str) -> bool:
    """Reject legacy tokens and tokens issued before a password change."""
    supplied = claims.get(SESSION_PASSWORD_CLAIM)
    if not isinstance(supplied, str) or not supplied:
        return False
    expected = password_fingerprint(password_hash)
    return hmac.compare_digest(supplied, expected)
