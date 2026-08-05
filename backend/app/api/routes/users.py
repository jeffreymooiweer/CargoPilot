from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.users import UserCreate, UserOut, UserRole, UserUpdate

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


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username exists")
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_delete_is_safe(user, admin, _active_admin_count(db))
    db.delete(user)
    db.commit()
    return {"ok": True}
