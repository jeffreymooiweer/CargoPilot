"""The settings endpoints: mine, everyone's, and the administrator's.

Three levels, and the split matters. ``/settings/me`` is scoped to the caller
and cannot reach another account. ``/settings/public`` is the handful of
instance facts the interface needs to draw itself correctly for any user.
``/settings/instance`` is the full picture, and is behind ``require_admin``
because it decides whether this installation talks to the internet at all.

Two routers, because the open application mounts only one of them. What the
interface needs to draw itself — the public facts and the option lists — is
on ``public_router`` and answers a visitor; the account's own settings and the
administrator's live on ``router`` and do not exist where there are no
accounts.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.settings import (
    MODALITIES,
    InstanceSettings,
    MailTestRequest,
    MailTestResult,
    PublicSettings,
    UserPreferences,
)
from app.services import mail, settings_store
from app.services.units import UNITS
from app.core.languages import SUPPORTED as SUPPORTED_LANGUAGES

router = APIRouter(prefix="/settings", tags=["settings"])
public_router = APIRouter(prefix="/settings", tags=["settings"])


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


@public_router.get("/public", response_model=PublicSettings)
def public_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return settings_store.public_settings(db)


@public_router.get("/options")
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
    return settings_store.redacted(settings_store.instance_settings(db))


@router.put("/instance", response_model=InstanceSettings)
def save_instance_settings(
    payload: InstanceSettings,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return settings_store.redacted(settings_store.save_instance_settings(db, payload))


@router.post("/instance/mail-test", response_model=MailTestResult)
def send_test_mail(
    payload: MailTestRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Prove the mail settings work, using the settings as they are stored.

    Deliberately not "test these values I am about to save": a test that
    passes on unsaved values and then fails on the saved ones would be worse
    than no test. Save first, then send.

    The recipient defaults to the administrator asking — the person who will
    know within seconds whether it arrived.
    """
    to = (payload.to or "").strip() or (admin.email or "")
    current = settings_store.instance_settings(db)
    try:
        mail.send_test(current, to)
    except mail.MailError as exc:
        # A refused password or an unreachable host is a fact about the
        # configuration, not a server fault: 400, with what the server said.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MailTestResult(ok=True, to=to)
