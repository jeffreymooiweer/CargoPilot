"""Forgetting a password, and getting back in without an administrator.

The properties pinned here are the ones a reset flow is judged on, and each
of them is a way this could have gone wrong:

1. **The form tells nobody who has an account.** "That address is not known
   here" is a membership oracle: try a list of addresses, learn who works
   where. Every request gets the same answer.
2. **The token is stored as a hash.** A reset token is a password in
   disguise; a database that leaks must not hand out working links.
3. **It expires, and it works once.** A link that is forwarded, logged by a
   mail scanner, or left in a browser history is not a standing key.
4. **Using it ends the old sessions.** Someone resets a password precisely
   when they suspect the old one is known to somebody else.
5. **The link points at the installation's own address**, not at the
   container name a reverse proxy happens to talk to.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import auth as auth_route
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.security import hash_password, verify_password
from app.main import app
from app.models.auth import PasswordResetToken
from app.models.user import User
from app.schemas.settings import InstanceSettings
from app.services import password_reset


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    get_settings.cache_clear()

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, username="ada", email="ada@example.com",
                     password_hash=hash_password("old-password"), role="admin"))
    session.add(User(id=2, username="bob", email="bob@example.com",
                     password_hash=hash_password("old-password"), role="user",
                     active=False))
    session.add(User(id=3, username="cor", email="",
                     password_hash=hash_password("old-password"), role="user"))
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


@pytest.fixture
def sent(db, monkeypatch):
    """A configured mail server that records instead of sending."""
    messages: list[dict] = []
    settings = InstanceSettings(
        mail_enabled=True, mail_host="smtp.example.com",
        mail_from="cargopilot@example.com")
    monkeypatch.setattr(auth_route, "instance_settings", lambda db: settings)
    monkeypatch.setattr(
        auth_route.mail, "send",
        lambda config, to, subject, body, attachments=None: messages.append(
            {"to": to, "subject": subject, "body": body}))
    return messages


@pytest.fixture
def client(db, monkeypatch):
    # The rate limit is real (and pinned below); it counts per client address,
    # and every test here comes from the same one. Left on, the tests would
    # start failing each other rather than the code.
    monkeypatch.setattr(auth_route.limiter, "enabled", False)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def limited_client(db):
    """The same client with the rate limit left switched on."""
    app.dependency_overrides[get_db] = lambda: db
    auth_route.limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    auth_route.limiter.reset()
    app.dependency_overrides.clear()


def link_from(message: dict) -> str:
    for word in message["body"].split():
        if word.startswith("http"):
            return word
    raise AssertionError(f"no link in the message: {message['body']}")


def token_from(message: dict) -> str:
    return link_from(message).split("token=", 1)[1]


# --- what the form gives away -----------------------------------------------


@pytest.mark.parametrize("identifier", [
    "ada", "ada@example.com",          # exists
    "nobody", "nobody@example.com",    # does not
    "bob",                             # exists but is deactivated
    "cor",                             # exists but has no address
    "",                                # nothing at all
])
def test_every_request_gets_the_same_answer(client, sent, identifier):
    response = client.post("/api/auth/forgot-password", json={"identifier": identifier})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_only_a_real_active_account_with_an_address_gets_a_message(client, sent):
    for identifier in ["nobody", "bob", "cor", ""]:
        client.post("/api/auth/forgot-password", json={"identifier": identifier})
    assert sent == []

    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    assert len(sent) == 1 and sent[0]["to"] == "ada@example.com"


def test_the_user_name_is_reachable_by_address_too(client, sent):
    client.post("/api/auth/forgot-password", json={"identifier": "ada@example.com"})
    assert len(sent) == 1


# --- the token itself -------------------------------------------------------


def test_the_database_holds_a_hash_and_not_the_token(client, sent, db):
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    token = token_from(sent[0])
    rows = db.query(PasswordResetToken).all()
    assert len(rows) == 1
    assert token not in rows[0].token_hash
    assert rows[0].token_hash == password_reset.hash_token(token)


def test_a_reset_sets_the_password_and_signs_the_old_sessions_out(client, sent, db):
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    response = client.post("/api/auth/reset-password", json={
        "token": token_from(sent[0]), "new_password": "a-brand-new-one"})
    assert response.status_code == 200

    db.expire_all()
    ada = db.get(User, 1)
    assert verify_password("a-brand-new-one", ada.password_hash)
    assert not verify_password("old-password", ada.password_hash)
    # The session token carries a fingerprint of the password hash, so every
    # sign-in from before the reset stops being accepted.
    assert client.post("/api/auth/login", json={
        "username": "ada", "password": "old-password"}).status_code == 401
    assert client.post("/api/auth/login", json={
        "username": "ada", "password": "a-brand-new-one"}).status_code == 200


def test_a_token_works_once(client, sent):
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    token = token_from(sent[0])
    assert client.post("/api/auth/reset-password", json={
        "token": token, "new_password": "first-new-password"}).status_code == 200
    second = client.post("/api/auth/reset-password", json={
        "token": token, "new_password": "second-new-password"})
    assert second.status_code == 400
    assert "no longer valid" in second.json()["detail"]


def test_an_expired_token_is_refused(client, sent, db):
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    token = token_from(sent[0])
    row = db.query(PasswordResetToken).first()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert client.post("/api/auth/reset-password", json={
        "token": token, "new_password": "a-brand-new-one"}).status_code == 400


def test_an_invented_token_is_refused(client):
    assert client.post("/api/auth/reset-password", json={
        "token": "x" * 40, "new_password": "a-brand-new-one"}).status_code == 400


def test_asking_twice_leaves_only_the_newest_link_working(client, sent):
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    first, second = token_from(sent[0]), token_from(sent[1])
    assert client.post("/api/auth/reset-password", json={
        "token": first, "new_password": "a-brand-new-one"}).status_code == 400
    assert client.post("/api/auth/reset-password", json={
        "token": second, "new_password": "a-brand-new-one"}).status_code == 200


def test_spending_a_token_drops_the_others_of_that_account(client, sent, db):
    """An attacker who requested a reset moments earlier must not keep a
    working link once the owner has used theirs."""
    ada = db.get(User, 1)
    attacker_token = password_reset.issue(db, ada)
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    owner_token = token_from(sent[-1])

    assert client.post("/api/auth/reset-password", json={
        "token": owner_token, "new_password": "a-brand-new-one"}).status_code == 200
    assert client.post("/api/auth/reset-password", json={
        "token": attacker_token, "new_password": "attacker-password"}).status_code == 400


def test_a_short_password_is_refused_before_the_token_is_spent(client, sent):
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    token = token_from(sent[0])
    assert client.post("/api/auth/reset-password", json={
        "token": token, "new_password": "short"}).status_code == 422
    # The link still works: a typo must not cost the reset.
    assert client.post("/api/auth/reset-password", json={
        "token": token, "new_password": "long-enough-now"}).status_code == 200


# --- the link ---------------------------------------------------------------


def test_the_link_follows_the_proxy_that_the_browser_actually_used(client, sent):
    client.post("/api/auth/forgot-password", json={"identifier": "ada"},
                headers={"x-forwarded-proto": "https",
                         "x-forwarded-host": "cargopilot.example.com"})
    assert link_from(sent[0]).startswith(
        "https://cargopilot.example.com/reset-password?token=")


def test_a_configured_address_wins_over_the_request(client, monkeypatch, db):
    """Only an administrator knows what the outside world calls this
    installation; a proxy that forwards nothing would otherwise put an
    internal host name in the mail."""
    messages: list[dict] = []
    settings = InstanceSettings(
        mail_enabled=True, mail_host="smtp.example.com",
        mail_from="cargopilot@example.com",
        public_url="https://cargopilot.nucraid.nl/")
    monkeypatch.setattr(auth_route, "instance_settings", lambda db: settings)
    monkeypatch.setattr(
        auth_route.mail, "send",
        lambda config, to, subject, body, attachments=None: messages.append(
            {"to": to, "subject": subject, "body": body}))

    client.post("/api/auth/forgot-password", json={"identifier": "ada"},
                headers={"x-forwarded-host": "internal-container:8000"})
    assert link_from(messages[0]).startswith(
        "https://cargopilot.nucraid.nl/reset-password?token=")


def test_the_message_says_what_to_do_and_what_not_doing_it_means(client, sent):
    client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    body = sent[0]["body"]
    assert "ada" in body
    assert "once" in body and "60 minutes" in body
    # Somebody who did not ask for this needs to know they can ignore it.
    assert "ignore" in body and "still works" in body


def test_without_a_mail_server_nothing_is_sent_and_nothing_is_said(client, db, monkeypatch):
    monkeypatch.setattr(auth_route, "instance_settings",
                        lambda db: InstanceSettings())
    response = client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    assert response.status_code == 200 and response.json() == {"ok": True}
    assert db.query(PasswordResetToken).count() == 0


def test_a_refusing_mail_server_does_not_change_the_answer(client, db, monkeypatch):
    """The person asking cannot fix the relay and must not be told about it;
    the administrator reads it in the log."""
    settings = InstanceSettings(
        mail_enabled=True, mail_host="smtp.example.com",
        mail_from="cargopilot@example.com")
    monkeypatch.setattr(auth_route, "instance_settings", lambda db: settings)

    def refusing(*args, **kwargs):
        raise auth_route.mail.MailError("Could not reach smtp.example.com:587")

    monkeypatch.setattr(auth_route.mail, "send", refusing)
    response = client.post("/api/auth/forgot-password", json={"identifier": "ada"})
    assert response.status_code == 200 and response.json() == {"ok": True}


def test_the_request_form_is_rate_limited(limited_client, sent):
    """Guessing addresses has to be slow. Without a limit the form is a list
    of everyone with an account, retrieved at the speed of the network."""
    codes = [
        limited_client.post("/api/auth/forgot-password",
                            json={"identifier": f"guess{n}@example.com"}).status_code
        for n in range(8)
    ]
    assert codes.count(200) == 5
    assert codes[-1] == 429
