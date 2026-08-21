import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.routes.auth import _public_base_url
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.users import (
    UserCreate,
    UserCreateResult,
    UserOut,
    UserRole,
    UserUpdate,
)
from app.services import mail, password_reset, two_factor
from app.services.settings_store import instance_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def _is_active_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN.value and bool(user.active)


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == UserRole.ADMIN.value, User.active.is_(True)).count()


def _ensure_update_is_safe(
    target: User,
    acting_admin: User,
    next_role: str,
    next_active: bool,
    active_admin_count: int,
) -> None:
    removes_admin_access = next_role != UserRole.ADMIN.value or not next_active

    if target.id == acting_admin.id and removes_admin_access:
        raise HTTPException(status_code=400, detail="Cannot deactivate or demote yourself")

    if _is_active_admin(target) and removes_admin_access and active_admin_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last active administrator")


def _ensure_delete_is_safe(target: User, acting_admin: User, active_admin_count: int) -> None:
    if target.id == acting_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if _is_active_admin(target) and active_admin_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last active administrator")


@router.get("", response_model=list[UserOut])
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserCreateResult)
def create_user(
    request: Request,
    payload: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Make an account, optionally inviting its owner to set a password.

    With an invitation there is no password to type here at all: the new
    colleague chooses their own through the link, so it never travels by
    chat or note and the administrator never knows it. Until they do, the
    account carries an unguessable random hash — an account nobody can sign
    in to, rather than one with a password somebody might guess.
    """
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username exists")

    current = instance_settings(db)
    invite = payload.send_welcome and mail.is_configured(current)
    if payload.password is None and not invite:
        raise HTTPException(
            status_code=400,
            detail="Give a password, or send an invitation so the account's "
                   "owner can choose one. That needs a mail server.")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password or secrets.token_urlsafe(32)),
        role=payload.role.value,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    result = UserCreateResult.model_validate(user, from_attributes=True)
    if not payload.send_welcome:
        return result
    if not invite:
        result.welcome_mail = "no_mail_server"
        return result

    token = password_reset.issue(db, user,
                                 ttl_minutes=password_reset.INVITE_TTL_MINUTES)
    link = password_reset.link_for(_public_base_url(request, current), token)
    try:
        mail.send(current, user.email, password_reset.WELCOME_SUBJECT,
                  password_reset.welcome_message(user, admin.username, link))
        result.welcome_mail = "sent"
    except mail.MailError as exc:
        # The account exists either way — deleting it again would be worse
        # than an administrator who now knows to pass the link on by hand.
        logger.warning("Could not send the invitation for %s: %s",
                       user.username, exc)
        result.welcome_mail = str(exc)
    return result


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    next_role = payload.role.value if payload.role is not None else user.role
    next_active = payload.active if payload.active is not None else bool(user.active)
    _ensure_update_is_safe(user, admin, next_role, next_active, _active_admin_count(db))

    if payload.email is not None:
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role.value
    if payload.active is not None:
        user.active = payload.active
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}/two-factor")
def clear_two_factor(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Remove somebody's second factor: the phone is gone and the recovery
    codes with it.

    Deliberately available to any administrator rather than only to the
    account's owner — that is the whole point of a way back in. It is also
    why an installation should have more than one administrator.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    two_factor.disable(db, user.id)
    logger.info("%s cleared the second factor of %s", admin.username, user.username)
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_delete_is_safe(user, admin, _active_admin_count(db))
    db.delete(user)
    db.commit()
    return {"ok": True}
