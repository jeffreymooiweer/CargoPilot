"""The settings endpoints: mine, everyone's, and the administrator's.

Three levels, and the split matters. ``/settings/me`` is scoped to the caller
and cannot reach another account. ``/settings/public`` is the handful of
instance facts the interface needs to draw itself correctly for any user.
``/settings/instance`` is the full picture, and is behind ``require_admin``
because it decides whether this installation talks to the internet at all.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.settings import (
    MODALITIES,
    InstanceSettings,
    PublicSettings,
    UserPreferences,
)
from app.services import settings_store
from app.services.units import UNITS
from app.core.languages import SUPPORTED as SUPPORTED_LANGUAGES

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/me", response_model=UserPreferences)
def my_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return settings_store.user_preferences(db, user.id)


@router.put("/me", response_model=UserPreferences)
def save_my_settings(
    payload: UserPreferences,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return settings_store.save_user_preferences(db, user.id, payload)


@router.get("/public", response_model=PublicSettings)
def public_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return settings_store.public_settings(db)


@router.get("/options")
def settings_options(user: User = Depends(get_current_user)):
    """What the settings screen may offer, from the backend that owns the lists.

    The languages, transport modes and units all already exist on the server.
    Repeating them in the interface is how two lists drift apart, so the screen
    asks instead.
    """
    return {
        "languages": list(SUPPORTED_LANGUAGES),
        "modalities": list(MODALITIES),
        "units": [{"code": unit.code, "symbol": unit.symbol} for unit in UNITS.values()],
    }


@router.get("/instance", response_model=InstanceSettings)
def instance_settings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return settings_store.instance_settings(db)


@router.put("/instance", response_model=InstanceSettings)
def save_instance_settings(
    payload: InstanceSettings,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return settings_store.save_instance_settings(db, payload)
