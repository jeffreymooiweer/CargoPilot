"""Regression tests for authentication cookies, sessions and administrator safety."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import Response

from app.api.routes import auth as auth_routes
from app.api.routes.users import delete_user, update_user
from app.core.database import Base
from app.core.security import (
    create_access_token,
    decode_access_token_claims,
    hash_password,
    token_matches_password,
)
from app.models.user import User
from app.schemas import UserRole, UserUpdate


def _request(scheme: str = "http", forwarded_proto: str | None = None) -> Request:
    headers = []
    if forwarded_proto is not None:
        headers.append((b"x-forwarded-proto", forwarded_proto.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": scheme,
            "path": "/api/auth/login",
            "raw_path": b"/api/auth/login",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 443 if scheme == "https" else 80),
        }
    )


def _settings(cookie_secure=None, trusted_proxy_headers=True):
    return SimpleNamespace(
        cookie_secure=cookie_secure,
        trusted_proxy_headers=trusted_proxy_headers,
        access_token_expire_minutes=480,
    )


def test_https_cookie_is_secure(monkeypatch):
    monkeypatch.setattr(auth_routes, "get_settings", lambda: _settings())
    response = Response()

    auth_routes.set_auth_cookie(response, _request(scheme="https"), "token")

    header = response.headers["set-cookie"]
    assert "Secure" in header
    assert "HttpOnly" in header
    assert "SameSite=lax" in header


def test_forwarded_https_cookie_is_secure_behind_trusted_proxy(monkeypatch):
    monkeypatch.setattr(auth_routes, "get_settings", lambda: _settings())
    assert auth_routes.cookie_is_secure(_request(forwarded_proto="https")) is True


def test_forwarded_proto_is_ignored_when_proxy_headers_are_disabled(monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "get_settings",
        lambda: _settings(trusted_proxy_headers=False),
    )
    assert auth_routes.cookie_is_secure(_request(forwarded_proto="https")) is False


def test_cookie_secure_setting_overrides_auto_detection(monkeypatch):
    monkeypatch.setattr(auth_routes, "get_settings", lambda: _settings(cookie_secure=False))
    assert auth_routes.cookie_is_secure(_request(scheme="https")) is False

    monkeypatch.setattr(auth_routes, "get_settings", lambda: _settings(cookie_secure=True))
    assert auth_routes.cookie_is_secure(_request(scheme="http")) is True


def test_password_change_invalidates_existing_token():
    old_hash = hash_password("old-password")
    token = create_access_token("alice", password_hash=old_hash, expires_minutes=5)
    claims = decode_access_token_claims(token)

    assert claims is not None
    assert token_matches_password(claims, old_hash) is True

    new_hash = hash_password("new-password")
    assert token_matches_password(claims, new_hash) is False


def test_legacy_token_without_password_fingerprint_is_not_accepted():
    token = create_access_token("alice", expires_minutes=5)
    claims = decode_access_token_claims(token)

    assert claims is not None
    assert token_matches_password(claims, hash_password("password")) is False


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _add_user(db, username: str, role: str = "user", active: bool = True) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=hash_password("password123"),
        role=role,
        active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_role_schema_rejects_unknown_roles():
    with pytest.raises(ValueError):
        UserUpdate(role="superadmin")


def test_admin_cannot_deactivate_itself(db):
    admin = _add_user(db, "admin", role=UserRole.ADMIN.value)

    with pytest.raises(HTTPException) as exc:
        update_user(admin.id, UserUpdate(active=False), admin=admin, db=db)

    assert exc.value.status_code == 400
    assert "own administrator access" in str(exc.value.detail)
    db.refresh(admin)
    assert admin.active is True


def test_last_active_admin_cannot_be_demoted(db):
    target = _add_user(db, "only-admin", role=UserRole.ADMIN.value)
    external_admin = SimpleNamespace(id=999)

    with pytest.raises(HTTPException) as exc:
        update_user(
            target.id,
            UserUpdate(role=UserRole.USER),
            admin=external_admin,
            db=db,
        )

    assert exc.value.status_code == 400
    assert "last active administrator" in str(exc.value.detail)


def test_one_of_two_active_admins_can_be_demoted(db):
    actor = _add_user(db, "actor", role=UserRole.ADMIN.value)
    target = _add_user(db, "target", role=UserRole.ADMIN.value)

    updated = update_user(
        target.id,
        UserUpdate(role=UserRole.USER),
        admin=actor,
        db=db,
    )

    assert updated.role == UserRole.USER.value
    assert actor.role == UserRole.ADMIN.value


def test_last_active_admin_cannot_be_deleted(db):
    target = _add_user(db, "only-admin", role=UserRole.ADMIN.value)
    external_admin = SimpleNamespace(id=999)

    with pytest.raises(HTTPException) as exc:
        delete_user(target.id, admin=external_admin, db=db)

    assert exc.value.status_code == 400
    assert "last active administrator" in str(exc.value.detail)
