"""Channels API + Instagram connect flow (Instagram HTTP calls are faked)."""

import os
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.helpers.crypto_helper import CryptoHelper
from app.models import (
    Feature, MembershipRole, Permission, Plan, PlanFeature, Role, RolePermission, SocialAccount,
    SocialAccountToken, Subscription, Tenant, TenantMembership, User, UserProfile,
)
from app.services.instagram_client import InstagramApiError, InstagramClient
from config.settings import get_settings

PASSWORD = "S3cret-pass!"


@pytest.fixture(autouse=True)
def instagram_settings(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "INSTAGRAM_APP_ID", "app-123")
    monkeypatch.setattr(s, "INSTAGRAM_APP_SECRET", "secret-xyz")
    monkeypatch.setattr(s, "INSTAGRAM_REDIRECT_URI", "https://example.ngrok-free.app/api/v1/channels/instagram/callback")
    monkeypatch.setattr(s, "ENCRYPTION_KEY", "unit-test-encryption-key")
    monkeypatch.setattr(s, "FRONTEND_URL", "http://localhost:3000")


class FakeInstagram:
    """Replaces the network parts of InstagramClient."""

    profiles = {"short-1": {"user_id": "17841400000001", "username": "rahul.fit", "account_type": "BUSINESS", "profile_picture_url": "http://img/1.jpg"}}
    fail_exchange = False

    @classmethod
    def install(cls, monkeypatch):
        monkeypatch.setattr(InstagramClient, "exchange_code", lambda self, code: cls._exchange(code))
        monkeypatch.setattr(InstagramClient, "long_lived_token", lambda self, tok: {"access_token": "long-" + tok, "expires_in": 5184000})
        monkeypatch.setattr(InstagramClient, "profile", lambda self, tok: cls.profiles[tok.removeprefix("long-")])

    @classmethod
    def _exchange(cls, code):
        if cls.fail_exchange:
            raise InstagramApiError("Invalid authorization code")
        return {"access_token": code, "user_id": 1, "permissions": ["instagram_business_basic"]}


@pytest.fixture
def world(db: Session, monkeypatch) -> dict:
    FakeInstagram.install(monkeypatch)
    FakeInstagram.fail_exchange = False
    perm = Permission(code="settings.manage")
    owner_role, agent_role = Role(code="owner", name="Owner", is_system=True), Role(code="agent", name="Agent", is_system=True)
    plan, feature = Plan(code="pro", name="Pro"), Feature(code="instagram_accounts", name="IG", value_type="integer")
    db.add_all([perm, owner_role, agent_role, plan, feature])
    db.flush()
    db.add_all([RolePermission(role_id=owner_role.id, permission_id=perm.id), PlanFeature(plan_id=plan.id, feature_id=feature.id, value_json=1)])

    def user(email):
        u = User(email=email, status="active")
        u.set_password(PASSWORD)
        db.add(u)
        db.flush()
        db.add(UserProfile(user_id=u.id, full_name=email))
        return u

    owner, agent, other_owner = user("owner@a.com"), user("agent@a.com"), user("owner@b.com")
    ta, tb = Tenant(name="A", slug="a", owner_user_id=owner.id), Tenant(name="B", slug="b", owner_user_id=other_owner.id)
    db.add_all([ta, tb])
    db.flush()
    for t, u, role in [(ta, owner, owner_role), (ta, agent, agent_role), (tb, other_owner, owner_role)]:
        m = TenantMembership(tenant_id=t.id, user_id=u.id, status="active")
        db.add(m)
        db.flush()
        db.add(MembershipRole(membership_id=m.id, role_id=role.id))
    db.add_all([Subscription(tenant_id=ta.id, plan_id=plan.id, status="active"), Subscription(tenant_id=tb.id, plan_id=plan.id, status="active")])
    db.commit()
    return {"ta": ta, "tb": tb, "owner": owner, "agent": agent, "other_owner": other_owner}


def headers(client: TestClient, email: str) -> dict:
    tok = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def start(client, world, email="owner@a.com", tenant="ta") -> str:
    r = client.post(f"/api/v1/companies/{world[tenant].id}/channels/instagram/connect", headers=headers(client, email))
    assert r.status_code == 200, r.text
    return parse_qs(urlparse(r.json()["data"]["authorize_url"]).query)["state"][0]


def callback(client, state, code="short-1", **extra):
    return client.get("/api/v1/channels/instagram/callback", params={"code": code, "state": state, **extra}, follow_redirects=False)


def test_connect_returns_instagram_authorize_url(client, world):
    r = client.post(f"/api/v1/companies/{world['ta'].id}/channels/instagram/connect", headers=headers(client, "owner@a.com"))
    url = urlparse(r.json()["data"]["authorize_url"])
    q = parse_qs(url.query)
    assert url.netloc == "www.instagram.com" and url.path == "/oauth/authorize"
    assert q["client_id"] == ["app-123"] and q["response_type"] == ["code"]
    assert q["redirect_uri"] == ["https://example.ngrok-free.app/api/v1/channels/instagram/callback"]
    assert "instagram_business_manage_messages" in q["scope"][0] and q["state"][0]
    assert "secret-xyz" not in r.text


def test_agent_cannot_connect_and_non_member_gets_404(client, world):
    r = client.post(f"/api/v1/companies/{world['ta'].id}/channels/instagram/connect", headers=headers(client, "agent@a.com"))
    assert r.status_code == 403
    r = client.post(f"/api/v1/companies/{world['ta'].id}/channels/instagram/connect", headers=headers(client, "owner@b.com"))
    assert r.status_code == 404
    assert client.post(f"/api/v1/companies/{world['ta'].id}/channels/instagram/connect").status_code == 401


def test_callback_saves_account_with_encrypted_token(client, world, db):
    r = callback(client, start(client, world))
    assert r.status_code == 302
    assert r.headers["location"] == f"http://localhost:3000/accounts/companies/{world['ta'].id}/channels?connected=instagram"
    acc = db.query(SocialAccount).one()
    assert acc.tenant_id == world["ta"].id and acc.username == "rahul.fit" and acc.platform_account_id == "17841400000001"
    assert acc.status == "connected" and acc.additional_attributes["profile_picture_url"] == "http://img/1.jpg"
    tok = db.query(SocialAccountToken).one()
    assert b"long-short-1" not in tok.access_token_encrypted  # never stored in plain text
    assert CryptoHelper.decrypt(tok.access_token_encrypted) == "long-short-1"
    assert tok.expires_at is not None


def test_channels_list_never_leaks_tokens(client, world):
    callback(client, start(client, world))
    r = client.get(f"/api/v1/companies/{world['ta'].id}/channels", headers=headers(client, "agent@a.com"))
    data = r.json()["data"]["channels"][0]
    assert data["configured"] is True and data["limit"] == 1
    assert data["accounts"][0]["username"] == "rahul.fit" and r.json()["data"]["can_manage"] is False
    assert "token" not in r.text and "long-short-1" not in r.text


def test_bad_state_and_denied_login_redirect_with_error(client, world, db):
    r = callback(client, "garbage")
    assert r.status_code == 302 and "channel_error" in r.headers["location"]
    assert db.query(SocialAccount).count() == 0
    state = start(client, world)
    r = client.get("/api/v1/channels/instagram/callback", params={"error": "access_denied", "error_description": "User denied", "state": state}, follow_redirects=False)
    assert "channel_error=User+denied" in r.headers["location"] and str(world["ta"].id) in r.headers["location"]


def test_instagram_failure_is_reported(client, world, db):
    FakeInstagram.fail_exchange = True
    r = callback(client, start(client, world))
    assert "Invalid+authorization+code" in r.headers["location"]
    assert db.query(SocialAccount).count() == 0


def test_account_cannot_be_stolen_by_another_company(client, world, db):
    callback(client, start(client, world))
    r = callback(client, start(client, world, "owner@b.com", "tb"))
    assert "already+connected+to+another+company" in r.headers["location"]
    assert db.query(SocialAccount).one().tenant_id == world["ta"].id


def test_plan_limit_and_reconnect(client, world, db):
    callback(client, start(client, world))
    FakeInstagram.profiles["short-2"] = {"user_id": "17841400000002", "username": "second", "account_type": "BUSINESS"}
    r = callback(client, start(client, world), code="short-2")
    assert "allows+1+Instagram" in r.headers["location"]
    # reconnecting the same account is fine and does not duplicate it
    r = callback(client, start(client, world))
    assert "connected=instagram" in r.headers["location"]
    assert db.query(SocialAccount).count() == 1 and db.query(SocialAccountToken).count() == 1


def test_disconnect_removes_token(client, world, db):
    callback(client, start(client, world))
    acc = db.query(SocialAccount).one()
    url = f"/api/v1/companies/{world['ta'].id}/channels/instagram/{acc.id}"
    assert client.delete(url, headers=headers(client, "agent@a.com")).status_code == 403
    assert client.delete(f"/api/v1/companies/{world['tb'].id}/channels/instagram/{acc.id}", headers=headers(client, "owner@b.com")).status_code == 404
    r = client.delete(url, headers=headers(client, "owner@a.com"))
    assert r.status_code == 200 and r.json()["data"]["status"] == "disconnected"
    db.expire_all()
    assert db.query(SocialAccountToken).count() == 0


def test_not_configured(client, world, monkeypatch):
    monkeypatch.setattr(get_settings(), "INSTAGRAM_APP_ID", "")
    r = client.post(f"/api/v1/companies/{world['ta'].id}/channels/instagram/connect", headers=headers(client, "owner@a.com"))
    assert r.status_code == 503
    assert client.get(f"/api/v1/companies/{world['ta'].id}/channels", headers=headers(client, "owner@a.com")).json()["data"]["channels"][0]["configured"] is False
