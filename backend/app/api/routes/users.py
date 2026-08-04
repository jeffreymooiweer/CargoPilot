from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas import UserCreate, UserOut, UserRole, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == UserRole.ADMIN.value, User.active.is_(True)).count()


def removes_active_admin_access(user: User, payload: UserUpdate) -> bool:
    next_role = payload.role.value if payload.role is not None else user.role
    next_active = payload.active if payload.active is not None else user.active
    return user.role == UserRole.ADMIN.value and user.active and (
        next_role != UserRole.ADMIN.value or not next_active
    )


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

    removing_access = removes_active_admin_access(user, payload)
    if user.id == admin.id and removing_access:
        raise HTTPException(status_code=400, detail="Cannot remove your own administrator access")
    if removing_access and active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last active administrator")

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
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if user.role == UserRole.ADMIN.value and user.active and active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last active administrator")
    db.delete(user)
    db.commit()
    return {"ok": True}
