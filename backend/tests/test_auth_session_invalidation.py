from types import SimpleNamespace

from starlette.requests import Request
from starlette.responses import Response

from app.api.routes.auth import _set_access_cookie, cookie_is_secure
from app.core.security import (
    create_access_token,
    decode_access_token_claims,
    hash_password,
    token_matches_password,
)


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
        secure_cookies=False,
        access_token_expire_minutes=480,
    )


def test_https_cookie_is_secure():
    settings = _settings()
    response = Response()

    _set_access_cookie(response, "token", settings, request=_request(scheme="https"))

    header = response.headers["set-cookie"]
    assert "Secure" in header
    assert "HttpOnly" in header
    assert "SameSite=lax" in header


def test_forwarded_https_is_secure_behind_trusted_proxy():
    settings = _settings()

    assert cookie_is_secure(_request(forwarded_proto="https"), settings) is True


def test_forwarded_proto_is_ignored_when_proxy_headers_are_disabled():
    settings = _settings(trusted_proxy_headers=False)

    assert cookie_is_secure(_request(forwarded_proto="https"), settings) is False


def test_explicit_cookie_setting_overrides_request_detection():
    assert cookie_is_secure(
        _request(scheme="https"), _settings(cookie_secure=False)
    ) is False
    assert cookie_is_secure(
        _request(scheme="http"), _settings(cookie_secure=True)
    ) is True


def test_password_change_invalidates_existing_token():
    old_hash = hash_password("old-password")
    token = create_access_token("alice", password_hash=old_hash, expires_minutes=5)
    claims = decode_access_token_claims(token)

    assert claims is not None
    assert token_matches_password(claims, old_hash) is True
    assert token_matches_password(claims, hash_password("new-password")) is False


def test_legacy_token_without_password_fingerprint_is_rejected():
    token = create_access_token("alice", expires_minutes=5)
    claims = decode_access_token_claims(token)

    assert claims is not None
    assert token_matches_password(claims, hash_password("password")) is False
