"""Auth + companies API: login, refresh, me, tenant isolation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Feature, Plan, PlanFeature, Role, Subscription, Tenant, TenantMembership, User, UserProfile, MembershipRole

PASSWORD = "S3cret-pass!"


def _user(db: Session, email: str, status: str = "active") -> User:
    u = User(email=email, status=status)
    u.set_password(PASSWORD)
    db.add(u)
    db.flush()
    db.add(UserProfile(user_id=u.id, full_name=email.split("@")[0].title()))
    return u


def _tenant(db: Session, name: str, owner: User, members: list[User]) -> Tenant:
    t = Tenant(name=name, slug=name.lower().replace(" ", "-"), owner_user_id=owner.id)
    db.add(t)
    db.flush()
    role = db.query(Role).filter_by(code="agent").first()
    for u in members:
        m = TenantMembership(tenant_id=t.id, user_id=u.id, status="active")
        db.add(m)
        db.flush()
        db.add(MembershipRole(membership_id=m.id, role_id=role.id))
    return t


@pytest.fixture
def world(db: Session) -> dict:
    db.add(Role(code="agent", name="Agent", is_system=True))
    plan = Plan(code="pro", name="Pro")
    feature = Feature(code="inbox", name="Inbox")
    db.add_all([plan, feature])
    db.flush()
    db.add(PlanFeature(plan_id=plan.id, feature_id=feature.id, value_json=True))
    a, b, outsider = _user(db, "a@one.com"), _user(db, "b@two.com"), _user(db, "out@three.com")
    blocked = _user(db, "blocked@one.com", status="blocked")
    lonely = _user(db, "lonely@x.com")
    t1 = _tenant(db, "Company One", a, [a, blocked])
    t2 = _tenant(db, "Company Two", b, [b, a])
    db.add(Subscription(tenant_id=t1.id, plan_id=plan.id, status="active"))
    db.commit()
    return {"t1": t1, "t2": t2, "a": a, "outsider": outsider, "lonely": lonely}


def _login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_returns_tokens_and_companies(client: TestClient, world: dict) -> None:
    r = _login(client, "A@One.com")  # email is case-insensitive
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["token_type"] == "bearer" and data["access_token"] and data["refresh_token"]
    assert data["user"]["full_name"] == "A"
    assert {c["name"] for c in data["companies"]} == {"Company One", "Company Two"}
    assert data["default_company_id"] == data["companies"][0]["id"]


@pytest.mark.parametrize("email,password,status", [
    ("a@one.com", "wrong-password", 401),
    ("nobody@nowhere.com", PASSWORD, 401),
    ("blocked@one.com", PASSWORD, 403),
    ("lonely@x.com", PASSWORD, 403),
    ("not-an-email", PASSWORD, 422),
])
def test_login_failures(client: TestClient, world: dict, email: str, password: str, status: int) -> None:
    r = _login(client, email, password)
    assert r.status_code == status
    assert r.json()["success"] is False


def test_unknown_email_and_wrong_password_look_the_same(client: TestClient, world: dict) -> None:
    assert _login(client, "a@one.com", "bad").json() == _login(client, "ghost@one.com", "bad").json()


def test_me_and_refresh(client: TestClient, world: dict) -> None:
    tokens = _login(client, "a@one.com").json()["data"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200 and me.json()["data"]["user"]["email"] == "a@one.com"
    assert client.get("/api/v1/auth/me").status_code == 401

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200 and refreshed.json()["data"]["access_token"]
    # an access token is not a refresh token, and vice versa
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401
    bad = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert bad.status_code == 401


def test_company_detail_includes_subscription_features(client: TestClient, world: dict) -> None:
    token = _login(client, "a@one.com").json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = client.get(f"/api/v1/companies/{world['t1'].id}", headers=h)
    assert r.status_code == 200
    sub = r.json()["data"]["subscription"]
    assert sub["has_access"] is True and sub["plan"] == "pro" and sub["features"] == {"inbox": True}
    # no subscription row: access is still granted while SUBSCRIPTION_ENFORCED is off
    r2 = client.get(f"/api/v1/companies/{world['t2'].id}", headers=h)
    assert r2.json()["data"]["subscription"]["has_access"] is True


def test_company_isolation(client: TestClient, world: dict) -> None:
    # outsider belongs to no company at all -> cannot even log in; a member of one company
    # must get 404 for another company's id.
    token = _login(client, "b@two.com").json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/api/v1/companies/{world['t2'].id}", headers=h).status_code == 200
    assert client.get(f"/api/v1/companies/{world['t1'].id}", headers=h).status_code == 404
    listing = client.get("/api/v1/companies", headers=h).json()["data"]
    assert [c["name"] for c in listing] == ["Company Two"]
