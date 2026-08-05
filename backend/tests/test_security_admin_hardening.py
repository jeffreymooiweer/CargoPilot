from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from app.api.routes.auth import _set_access_cookie
from app.api.routes.users import _ensure_delete_is_safe, _ensure_update_is_safe
from app.core.config import Settings
from app.schemas.users import UserCreate, UserRole, UserUpdate


def _settings(**overrides):
    return Settings(_env_file=None, **overrides)


def _user(user_id: int, role: str = "admin", active: bool = True):
    return SimpleNamespace(id=user_id, role=role, active=active)


def test_production_session_cookie_is_secure_by_default():
    response = Response()
    _set_access_cookie(response, "token", _settings(app_env="production"))

    cookie = response.headers["set-cookie"]
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_test_and_development_cookies_remain_usable_over_http():
    for environment in ("test", "development", "local"):
        response = Response()
        _set_access_cookie(response, "token", _settings(app_env=environment))
        assert "Secure" not in response.headers["set-cookie"]


def test_cookie_security_can_be_explicitly_overridden():
    response = Response()
    _set_access_cookie(
        response,
        "token",
        _settings(app_env="production", cookie_secure=False),
    )
    assert "Secure" not in response.headers["set-cookie"]


def test_user_roles_are_closed_to_admin_and_user():
    created = UserCreate(
        username="operator",
        email="operator@example.com",
        password="strong-password",
        role="admin",
    )
    assert created.role is UserRole.ADMIN
    assert UserUpdate(role="user").role is UserRole.USER

    with pytest.raises(ValidationError):
        UserCreate(
            username="operator",
            email="operator@example.com",
            password="strong-password",
            role="owner",
        )


def test_an_administrator_cannot_demote_or_deactivate_itself():
    admin = _user(1)

    with pytest.raises(HTTPException, match="deactivate or demote yourself"):
        _ensure_update_is_safe(admin, admin, "user", True, active_admin_count=2)

    with pytest.raises(HTTPException, match="deactivate or demote yourself"):
        _ensure_update_is_safe(admin, admin, "admin", False, active_admin_count=2)


def test_the_last_active_administrator_cannot_be_removed():
    acting_admin = _user(1)
    target = _user(2)

    with pytest.raises(HTTPException, match="last active administrator"):
        _ensure_update_is_safe(target, acting_admin, "user", True, active_admin_count=1)

    with pytest.raises(HTTPException, match="last active administrator"):
        _ensure_delete_is_safe(target, acting_admin, active_admin_count=1)


def test_another_administrator_can_be_changed_when_one_remains():
    acting_admin = _user(1)
    target = _user(2)

    _ensure_update_is_safe(target, acting_admin, "user", True, active_admin_count=2)
    _ensure_delete_is_safe(target, acting_admin, active_admin_count=2)


def test_an_administrator_cannot_delete_itself():
    admin = _user(1)

    with pytest.raises(HTTPException, match="Cannot delete yourself"):
        _ensure_delete_is_safe(admin, admin, active_admin_count=2)
