"""Enabling Instagram contact sync enqueues a job; the job writes contacts and conversations."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.helpers.crypto_helper import CryptoHelper
from app.jobs.instagram_send_job import InstagramSendJob
from app.jobs.instagram_sync_job import InstagramSyncJob
from app.models import (
    Contact, Feature, InstagramConnection, MembershipRole, Message, Permission, Plan, PlanFeature,
    Role, RolePermission, SocialAccount, Subscription, Tenant, TenantMembership, User, UserProfile,
)
from app.services.instagram_client import InstagramApiError, InstagramClient
from app.services.instagram_sync_service import InstagramSyncService
from config.settings import get_settings

PASSWORD = "S3cret-pass!"
IG_ID = "17841434828716856"
THREADS = [
    {
        "id": "thread-1",
        "participants": [
            {"id": IG_ID, "username": "the_ai_layer"},
            {"id": "999001", "username": "building_ats", "name": "Building ATS"},
        ],
        "messages": [
            {
                "id": "m-in",
                "created_time": "2026-10-30T06:10:00+0000",
                "from": {"id": "999001", "username": "building_ats"},
                "text": "Hi",
                "is_unsupported": False,
            },
            {
                "id": "m-out",
                "created_time": "2026-10-30T06:16:48+0000",
                "from": {"id": IG_ID, "username": "the_ai_layer"},
                "text": "Hello back",
                "is_unsupported": False,
            },
        ],
    }
]


@pytest.fixture(autouse=True)
def instagram_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "INSTAGRAM_APP_ID", "app-123")
    monkeypatch.setattr(settings, "INSTAGRAM_APP_SECRET", "secret-xyz")
    monkeypatch.setattr(settings, "INSTAGRAM_REDIRECT_URI", "https://example.ngrok-free.app/api/v1/channels/instagram/callback")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "unit-test-encryption-key")

    def fake_profile(self, ig_id, token):
        return {"id": ig_id, "username": "the_ai_layer", "name": "The AI Layer", "profile_picture_url": "http://img/p.jpg"}

    monkeypatch.setattr(InstagramClient, "business_profile", fake_profile)

    def fake_user_profile(self, igsid, token):
        return {
            "name": "Building ATS",
            "username": "building_ats",
            "profile_pic": "http://img/contact.jpg",
            "follower_count": 1200,
            "is_verified_user": True,
            "is_user_follow_business": True,
            "is_business_follow_user": False,
        }

    monkeypatch.setattr(InstagramClient, "user_profile", fake_user_profile)
    monkeypatch.setattr(
        "app.services.instagram_sync_service.save_profile_picture",
        lambda key, url: f"/profile-pictures/{key}.jpg" if url else None,
    )


@pytest.fixture
def world(db: Session) -> dict:
    manage, contacts_read, conversations_read, conversations_reply = (
        Permission(code="settings.manage"),
        Permission(code="contacts.read"),
        Permission(code="conversations.read"),
        Permission(code="conversations.reply"),
    )
    owner_role, agent_role = Role(code="owner", name="Owner", is_system=True), Role(code="agent", name="Agent", is_system=True)
    plan, feature = Plan(code="pro", name="Pro"), Feature(code="instagram_accounts", name="IG", value_type="integer")
    db.add_all([manage, contacts_read, conversations_read, conversations_reply, owner_role, agent_role, plan, feature])
    db.flush()
    db.add_all([
        RolePermission(role_id=owner_role.id, permission_id=manage.id),
        RolePermission(role_id=owner_role.id, permission_id=contacts_read.id),
        RolePermission(role_id=owner_role.id, permission_id=conversations_read.id),
        RolePermission(role_id=owner_role.id, permission_id=conversations_reply.id),
        PlanFeature(plan_id=plan.id, feature_id=feature.id, value_json=1),
    ])

    def user(email):
        row = User(email=email, status="active")
        row.set_password(PASSWORD)
        db.add(row)
        db.flush()
        db.add(UserProfile(user_id=row.id, full_name=email))
        return row

    owner, agent = user("owner@a.com"), user("agent@a.com")
    tenant = Tenant(name="A", slug="a", owner_user_id=owner.id)
    db.add(tenant)
    db.flush()
    for person, role in ((owner, owner_role), (agent, agent_role)):
        membership = TenantMembership(tenant_id=tenant.id, user_id=person.id, status="active")
        db.add(membership)
        db.flush()
        db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
    db.add(Subscription(tenant_id=tenant.id, plan_id=plan.id, status="active"))
    db.commit()
    return {"tenant": tenant, "owner": owner, "agent": agent}


def headers(client: TestClient, email: str) -> dict:
    token = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def connect(client: TestClient, world: dict) -> str:
    response = client.post(
        f"/api/v1/companies/{world['tenant'].id}/channels/instagram/connect",
        json={"instagram_app_id": IG_ID, "access_token": "EAA-secret-token"},
        headers=headers(client, "owner@a.com"),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


def test_enable_sync_enqueues_and_job_imports_threads(client, world, db, monkeypatch):
    connection_id = connect(client, world)
    queued: list[dict] = []
    monkeypatch.setattr(
        "app.controllers.contacts_controller.InstagramSyncJob.perform_later",
        lambda **kwargs: queued.append(kwargs),
    )

    def forbid_graph(self, ig_id, token):
        raise AssertionError("the request thread must not call Instagram")

    monkeypatch.setattr(InstagramClient, "message_threads", forbid_graph)
    response = client.post(
        f"/api/v1/companies/{world['tenant'].id}/contacts/instagram/{connection_id}/sync",
        headers=headers(client, "owner@a.com"),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["contact_sync_enabled"] is True and body["sync_status"] == "queued"
    assert queued == [{"connection_id": connection_id}]
    assert db.execute(select(Contact)).scalars().first() is None

    monkeypatch.setattr(InstagramClient, "message_threads", lambda self, ig_id, token: THREADS)
    counts = InstagramSyncService(db).run(uuid.UUID(connection_id))
    assert counts == {"contacts": 1, "conversations": 1, "messages": 2}
    db.expire_all()
    contact = db.execute(select(Contact)).scalars().one()
    assert contact.username == "building_ats" and contact.display_name == "Building ATS"
    assert contact.profile_picture_url == "/profile-pictures/999001.jpg" and contact.custom_fields["follower_count"] == 1200
    assert contact.custom_fields["fetched_at"]
    outbound = db.execute(select(Message).where(Message.direction == "outbound")).scalars().one()
    inbound = db.execute(select(Message).where(Message.direction == "inbound")).scalars().one()
    assert outbound.sender_type == "system" and outbound.sender_contact_id is None and outbound.content == "Hello back"
    assert inbound.sender_type == "contact" and inbound.sender_contact_id == contact.id and inbound.content == "Hi"
    assert db.execute(select(SocialAccount)).scalars().one().platform_account_id == IG_ID

    again = InstagramSyncService(db).run(uuid.UUID(connection_id))
    assert again == {"contacts": 0, "conversations": 0, "messages": 0}
    assert db.execute(select(Message)).scalars().all().__len__() == 2

    listed = client.get(f"/api/v1/companies/{world['tenant'].id}/contacts", headers=headers(client, "owner@a.com"))
    assert listed.status_code == 200
    assert listed.json()["data"]["contacts"][0]["username"] == "building_ats"
    assert listed.json()["data"]["contacts"][0]["profile_picture_url"] == "/profile-pictures/999001.jpg"
    conversations = client.get(f"/api/v1/companies/{world['tenant'].id}/conversations", headers=headers(client, "owner@a.com"))
    assert conversations.status_code == 200
    summary = conversations.json()["data"][0]
    assert summary["contact_name"] == "Building ATS" and summary["last_message"] == "Hello back"
    assert summary["contact_profile_picture_url"] == "/profile-pictures/999001.jpg" and summary["is_verified_user"] is True
    detail = client.get(
        f"/api/v1/companies/{world['tenant'].id}/conversations/{summary['id']}",
        headers=headers(client, "owner@a.com"),
    )
    assert [item["content"] for item in detail.json()["data"]["messages"]] == ["Hi", "Hello back"]
    assert CryptoHelper.decrypt(db.get(InstagramConnection, uuid.UUID(connection_id)).access_token_encrypted) == "EAA-secret-token"


def _imported(client, world, db, monkeypatch) -> tuple[str, str]:
    connection_id = connect(client, world)
    monkeypatch.setattr(InstagramClient, "message_threads", lambda self, ig_id, token: THREADS)
    service = InstagramSyncService(db)
    service.enable(world["tenant"].id, uuid.UUID(connection_id), world["owner"].id)
    service.run(uuid.UUID(connection_id))
    db.expire_all()
    summary = client.get(
        f"/api/v1/companies/{world['tenant'].id}/conversations",
        headers=headers(client, "owner@a.com"),
    ).json()["data"][0]
    return connection_id, summary["id"]


def test_reply_enqueues_and_job_sends(client, world, db, monkeypatch):
    connection_id, conversation_id = _imported(client, world, db, monkeypatch)
    queued: list[dict] = []
    monkeypatch.setattr("app.controllers.conversations_controller.InstagramSendJob.perform_later", lambda **kwargs: queued.append(kwargs))

    def forbid_send(self, *args, **kwargs):
        raise AssertionError("the request thread must not send")

    monkeypatch.setattr(InstagramClient, "send_text", forbid_send)
    blank = client.post(
        f"/api/v1/companies/{world['tenant'].id}/conversations/{conversation_id}/messages",
        json={"text": "   "},
        headers=headers(client, "owner@a.com"),
    )
    assert blank.status_code == 400
    response = client.post(
        f"/api/v1/companies/{world['tenant'].id}/conversations/{conversation_id}/messages",
        json={"text": "From the CRM"},
        headers=headers(client, "owner@a.com"),
    )
    assert response.status_code == 200, response.text
    sent = response.json()["data"]["messages"][-1]
    assert sent["content"] == "From the CRM" and sent["direction"] == "outbound" and sent["status"] == "queued"
    assert queued == [{"message_id": sent["id"]}]
    db.expire_all()
    row = db.get(Message, uuid.UUID(sent["id"]))
    assert row.sender_type == "agent" and row.sender_membership_id is not None and row.external_message_id is None

    seen = {}

    def fake_send(self, ig_id, recipient_id, token, text, tag=None):
        seen.update(ig_id=ig_id, recipient_id=recipient_id, token=token, text=text, tag=tag)
        return {"recipient_id": recipient_id, "message_id": "mid-1"}

    monkeypatch.setattr(InstagramClient, "send_text", fake_send)
    assert InstagramSyncService(db).deliver(row.id) == {"status": "sent"}
    db.expire_all()
    assert row.status == "sent" and row.external_message_id == "mid-1"
    assert seen == {"ig_id": IG_ID, "recipient_id": "999001", "token": "EAA-secret-token", "text": "From the CRM", "tag": None}
    assert CryptoHelper.decrypt(db.get(InstagramConnection, uuid.UUID(connection_id)).access_token_encrypted) == "EAA-secret-token"

    def rejected(self, ig_id, recipient_id, token, text):
        raise InstagramApiError("(#10) Application does not have permission")

    monkeypatch.setattr(InstagramClient, "send_text", rejected)
    again = client.post(
        f"/api/v1/companies/{world['tenant'].id}/conversations/{conversation_id}/messages",
        json={"text": "Second"},
        headers=headers(client, "owner@a.com"),
    )
    failed_id = uuid.UUID(again.json()["data"]["messages"][-1]["id"])
    assert InstagramSyncService(db).deliver(failed_id) == {"status": "failed"}
    db.expire_all()
    failed = db.get(Message, failed_id)
    assert failed.status == "failed" and "permission" in failed.additional_attributes["send_error"]

    calls: list[str | None] = []

    def window_then_tag(self, ig_id, recipient_id, token, text, tag=None):
        calls.append(tag)
        if tag is None:
            raise InstagramApiError("(#10) This message is sent outside of allowed window.")
        return {"recipient_id": recipient_id, "message_id": "mid-2"}

    monkeypatch.setattr(InstagramClient, "send_text", window_then_tag)
    late = client.post(
        f"/api/v1/companies/{world['tenant'].id}/conversations/{conversation_id}/messages",
        json={"text": "Later reply"},
        headers=headers(client, "owner@a.com"),
    )
    late_id = uuid.UUID(late.json()["data"]["messages"][-1]["id"])
    assert InstagramSyncService(db).deliver(late_id) == {"status": "sent"}
    db.expire_all()
    assert db.get(Message, late_id).status == "sent" and db.get(Message, late_id).external_message_id == "mid-2"
    assert calls == [None, "HUMAN_AGENT"]

    def both_blocked(self, ig_id, recipient_id, token, text, tag=None):
        if tag is None:
            raise InstagramApiError("(#10) This message is sent outside of allowed window.")
        raise InstagramApiError("(#10) Human Agent is not approved")

    monkeypatch.setattr(InstagramClient, "send_text", both_blocked)
    blocked = client.post(
        f"/api/v1/companies/{world['tenant'].id}/conversations/{conversation_id}/messages",
        json={"text": "Too late"},
        headers=headers(client, "owner@a.com"),
    )
    blocked_id = uuid.UUID(blocked.json()["data"]["messages"][-1]["id"])
    assert InstagramSyncService(db).deliver(blocked_id) == {"status": "failed"}
    db.expire_all()
    assert "24 hours" in db.get(Message, blocked_id).additional_attributes["send_error"]


def test_agent_cannot_reply(client, world, db, monkeypatch):
    _, conversation_id = _imported(client, world, db, monkeypatch)
    response = client.post(
        f"/api/v1/companies/{world['tenant'].id}/conversations/{conversation_id}/messages",
        json={"text": "Nope"},
        headers=headers(client, "agent@a.com"),
    )
    assert response.status_code == 403


def test_agent_cannot_enable_sync(client, world):
    connection_id = connect(client, world)
    response = client.post(
        f"/api/v1/companies/{world['tenant'].id}/contacts/instagram/{connection_id}/sync",
        headers=headers(client, "agent@a.com"),
    )
    assert response.status_code == 403


def test_job_perform_uses_the_service(monkeypatch):
    seen = {}

    class FakeService:
        def __init__(self, db):
            seen["db"] = db

        def run(self, connection_id):
            seen["connection_id"] = connection_id
            return {"contacts": 0, "conversations": 0, "messages": 0}

    class FakeSession:
        def close(self):
            seen["closed"] = True

    monkeypatch.setattr("app.services.instagram_sync_service.InstagramSyncService", FakeService)
    monkeypatch.setattr("config.database.SessionLocal", lambda: FakeSession())
    result = InstagramSyncJob().perform(connection_id=str(uuid.uuid4()))
    assert result["messages"] == 0 and seen["closed"] is True


def test_send_job_uses_the_service(monkeypatch):
    seen = {}

    class FakeService:
        def __init__(self, db):
            seen["db"] = db

        def deliver(self, message_id):
            seen["message_id"] = message_id
            return {"status": "sent"}

    class FakeSession:
        def close(self):
            seen["closed"] = True

    message_id = uuid.uuid4()
    monkeypatch.setattr("app.services.instagram_sync_service.InstagramSyncService", FakeService)
    monkeypatch.setattr("config.database.SessionLocal", lambda: FakeSession())
    assert InstagramSendJob().perform(message_id=str(message_id)) == {"status": "sent"}
    assert seen["message_id"] == message_id and seen["closed"] is True
