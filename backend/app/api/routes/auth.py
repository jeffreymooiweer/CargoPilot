import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.users import (
    LoginRequest,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserOut,
)
from app.services import mail, password_reset
from app.services.settings_store import instance_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


def cookie_is_secure(request: Request, settings: Settings | None = None) -> bool:
    """Determine the Secure flag from explicit config or the actual request."""
    settings = settings or get_settings()
    if settings.cookie_secure is not None:
        return settings.cookie_secure
    if request.url.scheme.lower() == "https":
        return True
    if settings.trusted_proxy_headers:
        forwarded = request.headers.get("x-forwarded-proto", "")
        return forwarded.split(",", 1)[0].strip().lower() == "https"
    return False


def _set_access_cookie(
    response: Response,
    token: str,
    settings: Settings,
    request: Request | None = None,
    expire_minutes: int | None = None,
) -> None:
    secure = cookie_is_secure(request, settings) if request is not None else settings.secure_cookies
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        # The cookie must not outlive the token it carries, or the browser keeps
        # sending a session the server has already stopped accepting.
        max_age=(expire_minutes or settings.access_token_expire_minutes) * 60,
        path="/",
    )


def _clear_access_cookie(
    response: Response,
    settings: Settings,
    request: Request | None = None,
) -> None:
    secure = cookie_is_secure(request, settings) if request is not None else settings.secure_cookies
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
    expire_minutes = instance_settings(db).session_timeout_minutes
    token = create_access_token(
        user.username, password_hash=user.password_hash, expires_minutes=expire_minutes
    )
    _set_access_cookie(response, token, get_settings(), request=request, expire_minutes=expire_minutes)
    return {"user": UserOut.model_validate(user)}


@router.post("/logout")
def logout(request: Request, response: Response):
    _clear_access_cookie(response, get_settings(), request=request)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": UserOut.model_validate(user), "admin_ready": True}


@router.get("/setup-status")
def setup_status(db: Session = Depends(get_db)):
    has_admin = db.query(User).filter(User.role == "admin").first() is not None
    return {"has_admin": has_admin}


def _public_base_url(request: Request, settings_row) -> str:
    """Where to point the links in outgoing mail.

    The configured address wins, because only an administrator knows what
    the outside world calls this installation. Without one the request is
    read — including the proxy's own headers when those are trusted, which
    is the difference between a working link and one pointing at an
    internal container name.
    """
    configured = (settings_row.public_url or "").strip()
    if configured:
        return configured.rstrip("/")
    scheme = request.url.scheme
    host = request.url.netloc
    if get_settings().trusted_proxy_headers:
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        forwarded_host = request.headers.get("x-forwarded-host", "")
        if forwarded_proto:
            scheme = forwarded_proto.split(",", 1)[0].strip()
        if forwarded_host:
            host = forwarded_host.split(",", 1)[0].strip()
    return f"{scheme}://{host}"


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Ask for a reset link.

    The answer never changes. Whether the account exists, whether it is
    active, whether it has an address, whether the mail server accepted the
    message: none of it is visible here, or this form becomes a way to
    enumerate who has an account, one guess at a time. What went wrong is
    written to the log, where the administrator can see it and an outsider
    cannot.
    """
    user = password_reset.find_account(db, payload.identifier)
    current = instance_settings(db)
    if user is not None and mail.is_configured(current):
        token = password_reset.issue(db, user)
        link = password_reset.link_for(_public_base_url(request, current), token)
        try:
            mail.send(current, user.email, password_reset.SUBJECT,
                      password_reset.message_for(user, link))
        except mail.MailError as exc:
            logger.warning("Could not send the reset mail for %s: %s",
                           user.username, exc)
    elif user is not None:
        logger.warning(
            "%s asked for a password reset, but no mail server is configured",
            user.username)
    return {"ok": True}


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(
    request: Request,
    payload: PasswordResetConfirm,
    response: Response,
    db: Session = Depends(get_db),
):
    """Spend a reset link and set the new password.

    Unknown, expired and already-used tokens get one and the same answer:
    the difference between them is only useful to somebody guessing.
    """
    user = password_reset.redeem(db, payload.token)
    if user is None:
        raise HTTPException(
            status_code=400,
            detail="This reset link is no longer valid. Ask for a new one.")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    password_reset.spend(db, payload.token)
    # Every session signed in with the old password stops working: the token
    # fingerprint follows the password hash. Clearing the cookie here means
    # the browser that just reset does not carry a dead session either.
    _clear_access_cookie(response, get_settings(), request=request)
    return {"ok": True}


@router.post("/change-password")
def change_password(
    request: Request,
    payload: PasswordChange,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    _clear_access_cookie(response, get_settings(), request=request)
    return {"ok": True, "reauthenticate": True}
