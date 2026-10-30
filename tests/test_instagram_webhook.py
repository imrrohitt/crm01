"""Meta webhook handshake and inbound Instagram message storage."""

import hashlib
import hmac
import json

from app.models import WebhookEvent
from config.settings import get_settings

VERIFY = "my_crm_verify_token_2024"
PATH = "/api/v1/channels/instagram/webhook"
PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841434828716856",
            "time": 1730000000,
            "messaging": [
                {
                    "sender": {"id": "igsid-1"},
                    "recipient": {"id": "17841434828716856"},
                    "timestamp": 1730000001,
                    "message": {"mid": "m.1", "text": "Mujhe guidance chahiye"},
                }
            ],
        }
    ],
}


def test_verify_returns_challenge(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "INSTAGRAM_VERIFY_TOKEN", VERIFY)
    r = client.get(PATH, params={"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "12345"})
    assert r.status_code == 200
    assert r.text == "12345"


def test_verify_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "INSTAGRAM_VERIFY_TOKEN", VERIFY)
    r = client.get(PATH, params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "12345"})
    assert r.status_code == 403


def test_post_stores_message_and_ignores_retry(client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "INSTAGRAM_APP_SECRET", "")
    body = json.dumps(PAYLOAD).encode()
    r = client.post(PATH, content=body, headers={"content-type": "application/json"})
    assert r.status_code == 200 and r.text == "EVENT_RECEIVED"
    db.expire_all()
    event = db.query(WebhookEvent).one()
    assert event.provider == "meta"
    assert event.provider_event_id == hashlib.sha256(body).hexdigest()
    assert event.event_type == "message"
    assert event.payload["entry"][0]["messaging"][0]["message"]["text"] == "Mujhe guidance chahiye"
    again = client.post(PATH, content=body, headers={"content-type": "application/json"})
    assert again.status_code == 200
    db.expire_all()
    assert db.query(WebhookEvent).count() == 1


def test_post_rejects_bad_signature(client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "INSTAGRAM_APP_SECRET", "app-secret")
    body = json.dumps(PAYLOAD).encode()
    r = client.post(PATH, content=body, headers={"content-type": "application/json", "x-hub-signature-256": "sha256=deadbeef"})
    assert r.status_code == 403
    assert db.query(WebhookEvent).count() == 0
    good = hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
    ok = client.post(PATH, content=body, headers={"content-type": "application/json", "x-hub-signature-256": f"sha256={good}"})
    assert ok.status_code == 200
    db.expire_all()
    assert db.query(WebhookEvent).count() == 1
