"""Reading and writing settings, with the environment as the starting point.

The rule this module exists to enforce: **an installation that never opens the
settings screen keeps behaving exactly as its ``.env`` says.** The environment
variables were the only way to configure CargoPilot until v1.45.0, they are
documented in ``docs/configuration.md``, and quietly overriding them with a
hard-coded default would change working installations on upgrade.

So a stored setting is an *overlay*. :func:`instance_settings` starts from the
environment, lays the saved JSON over it, and returns the result. Nothing is
written until an administrator actually saves something, and only the keys they
saved take precedence from then on.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.settings import InstanceSetting, UserPreference
from app.schemas.settings import InstanceSettings, PublicSettings, UserPreferences

logger = logging.getLogger(__name__)


def _load_json(raw: str | None) -> dict[str, Any]:
    """The stored payload, or an empty overlay when it cannot be read.

    A settings row that somehow holds invalid JSON must not take the whole
    application down: falling back to the defaults leaves a working app that an
    administrator can fix from the screen itself.
    """
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("Stored settings are not valid JSON; falling back to defaults")
        return {}
    return value if isinstance(value, dict) else {}


def environment_defaults() -> InstanceSettings:
    """The instance settings as the environment variables describe them."""
    settings = get_settings()
    return InstanceSettings(
        address_api_url=settings.geo_address_api_url,
        address_timeout_seconds=settings.geo_address_timeout_seconds,
        catalog_auto_sync=settings.catalog_auto_sync,
        update_check_enabled=settings.update_check_enabled,
        session_timeout_minutes=settings.access_token_expire_minutes,
        # A host in the environment is a deliberate act, so it switches
        # sending on; without one the mail settings stay off and empty.
        mail_enabled=bool(settings.smtp_host and settings.smtp_from),
        mail_host=settings.smtp_host,
        mail_port=settings.smtp_port,
        mail_security=_known_security(settings.smtp_security),
        mail_username=settings.smtp_username,
        mail_password=settings.smtp_password,
        mail_from=settings.smtp_from,
        mail_from_name=settings.smtp_from_name,
        mail_timeout_seconds=settings.smtp_timeout_seconds,
    )


def _known_security(value: str) -> str:
    """An unreadable SMTP_SECURITY must not make the whole settings screen
    fail to load; STARTTLS is both the common case and the safe one."""
    value = (value or "").strip().lower()
    return value if value in ("starttls", "ssl", "none") else "starttls"


def redacted(settings: InstanceSettings) -> InstanceSettings:
    """The instance settings as they may leave the server.

    The mail password is the one value here that is a secret rather than a
    configuration choice. It is stored, it is used when sending, and it is
    never sent to a browser — ``mail_password_set`` says whether one exists,
    which is all the screen needs to draw itself honestly.
    """
    return settings.model_copy(update={"mail_password": ""})


def instance_settings(db: Session) -> InstanceSettings:
    """The effective instance settings: environment first, saved values on top.

    The mail password comes back in full — this is what the mail service
    reads. The API redacts it on the way out; see :func:`redacted`.
    """
    row = db.query(InstanceSetting).order_by(InstanceSetting.id).first()
    stored = _load_json(row.data_json if row else None)
    if not stored:
        return _with_password_flag(environment_defaults())
    merged = environment_defaults().model_dump()
    merged.update({key: value for key, value in stored.items() if key in merged})
    try:
        return _with_password_flag(InstanceSettings(**merged))
    except ValueError:
        # A value that was valid when it was written but no longer passes
        # validation (a language that was dropped, say) must not lock everyone
        # out of the app. Keep the fields that still validate.
        logger.warning("Stored instance settings are partly invalid; using defaults for those fields")
        safe = environment_defaults()
        for key, value in stored.items():
            if key not in merged:
                continue
            try:
                safe = InstanceSettings(**{**safe.model_dump(), key: value})
            except ValueError:
                continue
        return _with_password_flag(safe)


def _with_password_flag(settings: InstanceSettings) -> InstanceSettings:
    """``mail_password_set`` is derived, never stored and never trusted from
    input: it says whether the password field holds anything at all."""
    return settings.model_copy(
        update={"mail_password_set": bool(settings.mail_password)})


def save_instance_settings(db: Session, values: InstanceSettings) -> InstanceSettings:
    row = db.query(InstanceSetting).order_by(InstanceSetting.id).first()
    if row is None:
        row = InstanceSetting(id=1)
        db.add(row)
    if not values.mail_password:
        # The screen never receives the stored password, so it cannot send it
        # back. An empty field means "leave it alone" — otherwise changing the
        # port would silently clear the password and break sending.
        values = values.model_copy(
            update={"mail_password": instance_settings(db).mail_password})
    row.data_json = values.model_dump_json()
    db.commit()
    return instance_settings(db)


def public_settings(db: Session) -> PublicSettings:
    """The subset any signed-in user is allowed to read."""
    current = instance_settings(db)
    return PublicSettings(
        default_language=current.default_language,
        default_theme=current.default_theme,
        address_lookup_enabled=current.address_lookup_enabled,
        un_cards_enabled=current.un_cards_enabled,
        organisation_name=current.organisation_name,
        organisation_address=current.organisation_address,
    )


def user_preferences(db: Session, user_id: int) -> UserPreferences:
    """One user's preferences, with the instance defaults filling the gaps."""
    row = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    stored = _load_json(row.data_json if row else None)
    defaults = UserPreferences().model_dump()
    merged = {**defaults, **{key: value for key, value in stored.items() if key in defaults}}
    try:
        preferences = UserPreferences(**merged)
    except ValueError:
        logger.warning("Stored preferences for user %s are partly invalid; using defaults", user_id)
        preferences = UserPreferences()

    instance = instance_settings(db)
    if not preferences.language:
        preferences.language = instance.default_language
    if not stored.get("theme"):
        preferences.theme = instance.default_theme
    if not preferences.consignor_name and not preferences.consignor_address:
        # A new colleague should not have to type the company that is already
        # configured for the installation.
        preferences.consignor_name = instance.organisation_name
        preferences.consignor_address = instance.organisation_address
    return preferences


def save_user_preferences(db: Session, user_id: int, values: UserPreferences) -> UserPreferences:
    row = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if row is None:
        row = UserPreference(user_id=user_id)
        db.add(row)
    row.data_json = values.model_dump_json()
    db.commit()
    return user_preferences(db, user_id)
