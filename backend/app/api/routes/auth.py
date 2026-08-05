from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.users import LoginRequest, PasswordChange, UserOut

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
) -> None:
    secure = cookie_is_secure(request, settings) if request is not None else settings.secure_cookies
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=settings.access_token_expire_minutes * 60,
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
    token = create_access_token(user.username, password_hash=user.password_hash)
    _set_access_cookie(response, token, get_settings(), request=request)
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
