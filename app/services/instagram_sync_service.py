"""
Turn Instagram DM threads into contacts, conversations, and messages.

The HTTP request only flips sync on and enqueues a job. This service runs inside that job.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.helpers.crypto_helper import CryptoHelper
from app.models import Contact, Conversation, InstagramConnection, Message, SocialAccount
from app.services.instagram_client import InstagramApiError, InstagramClient
from app.services.instagram_service import ConnectError
from app.services.profile_picture_store import save_profile_picture


TEXT_LIMIT = 1000


class InstagramSyncService:
    def __init__(self, db: Session, client: InstagramClient | None = None) -> None:
        self.db = db
        self.client = client or InstagramClient()

    def enable(self, tenant_id: uuid.UUID, connection_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
        """Mark this Instagram account for contact sync and return the public sync state. Does not call Instagram."""
        connection = self._connection(tenant_id, connection_id)
        account = self._ensure_social_account(connection, user_id)
        attrs = dict(connection.additional_attributes or {})
        attrs.update({"contact_sync_enabled": True, "social_account_id": str(account.id), "sync_status": "queued", "sync_error": None})
        connection.additional_attributes = attrs
        self.db.commit()
        return self._state(connection)

    def run(self, connection_id: uuid.UUID) -> dict[str, int]:
        """Import every DM thread for one connection. Called by the Celery job."""
        connection = self.db.get(InstagramConnection, connection_id)
        if connection is None or connection.status != "connected":
            raise ConnectError("Instagram account is not connected.")
        if not (connection.additional_attributes or {}).get("contact_sync_enabled"):
            raise ConnectError("Contact sync is not enabled for this account.")
        self._set_status(connection, "running", None)
        try:
            token = CryptoHelper.decrypt(connection.access_token_encrypted)
            self._refresh_account_profile(connection, token)
            threads = self.client.message_threads(connection.instagram_app_id, token)
            counts = self._import_threads(connection, token, threads)
        except (InstagramApiError, Exception) as exc:
            self.db.rollback()
            connection = self.db.get(InstagramConnection, connection_id)
            if connection is not None:
                message = getattr(exc, "message", None) or str(exc)
                self._set_status(connection, "failed", message[:500])
            raise
        connection = self.db.get(InstagramConnection, connection_id)
        if connection is not None:
            self._set_status(connection, "synced", None)
        return counts

    def accounts(self, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(InstagramConnection).where(
                InstagramConnection.tenant_id == tenant_id, InstagramConnection.status == "connected"
            ).order_by(InstagramConnection.created_at)
        ).scalars()
        return [self._state(row) for row in rows]

    def contacts(self, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(Contact).where(Contact.tenant_id == tenant_id).order_by(Contact.last_interaction_at.desc().nullslast(), Contact.created_at.desc())
        ).scalars()
        return [self._contact_public(row) for row in rows]

    def conversations(self, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = list(self.db.execute(
            select(Conversation).where(Conversation.tenant_id == tenant_id).order_by(Conversation.last_message_at.desc().nullslast())
        ).scalars())
        contacts = {row.id: row for row in self.db.execute(select(Contact).where(Contact.tenant_id == tenant_id)).scalars()}
        previews = self._latest_messages([row.id for row in rows])
        return [self._conversation_public(row, contacts.get(row.contact_id), previews.get(row.id)) for row in rows]

    def queue_reply(self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, membership_id: uuid.UUID, text: str) -> uuid.UUID:
        """Store an outbound message as queued. The request returns after this; Celery sends it."""
        body = text.strip()
        if not body:
            raise ConnectError("Write a message before sending.")
        if len(body) > TEXT_LIMIT:
            raise ConnectError(f"Instagram messages can be at most {TEXT_LIMIT} characters.")
        conversation = self.db.get(Conversation, conversation_id)
        if conversation is None or conversation.tenant_id != tenant_id:
            raise ConnectError("Conversation not found.", status=404)
        contact = self.db.get(Contact, conversation.contact_id)
        if contact is None or not contact.platform_user_id:
            raise ConnectError("This contact has no Instagram id.")
        account = self.db.get(SocialAccount, conversation.social_account_id)
        connection = None
        if account is not None:
            connection = self.db.execute(
                select(InstagramConnection).where(
                    InstagramConnection.tenant_id == tenant_id,
                    InstagramConnection.instagram_app_id == account.platform_account_id,
                    InstagramConnection.status == "connected",
                )
            ).scalars().first()
        if connection is None:
            raise ConnectError("Instagram account is not connected.", status=404)
        now = datetime.now(timezone.utc)
        message = Message(
            tenant_id=tenant_id,
            social_account_id=conversation.social_account_id,
            conversation_id=conversation.id,
            direction="outbound",
            sender_type="agent",
            sender_membership_id=membership_id,
            content=body,
            message_type="text",
            status="queued",
            sent_at=now,
        )
        self.db.add(message)
        conversation.last_message_at = now
        contact.last_interaction_at = now
        self.db.commit()
        return message.id

    def deliver(self, message_id: uuid.UUID) -> dict[str, str]:
        """Send one queued message. Called by the Celery job, never by the HTTP request."""
        message = self.db.get(Message, message_id)
        if message is None or message.status != "queued":
            return {"status": message.status if message else "missing"}
        conversation = self.db.get(Conversation, message.conversation_id)
        contact = self.db.get(Contact, conversation.contact_id) if conversation else None
        account = self.db.get(SocialAccount, message.social_account_id)
        connection = None
        if account is not None:
            connection = self.db.execute(
                select(InstagramConnection).where(
                    InstagramConnection.tenant_id == message.tenant_id,
                    InstagramConnection.instagram_app_id == account.platform_account_id,
                    InstagramConnection.status == "connected",
                )
            ).scalars().first()
        if connection is None or contact is None or not contact.platform_user_id:
            self._mark_failed(message, "Instagram account is not connected.")
            return {"status": "failed"}
        token = CryptoHelper.decrypt(connection.access_token_encrypted)
        text = message.content or ""
        try:
            result = self.client.send_text(connection.instagram_app_id, contact.platform_user_id, token, text)
        except InstagramApiError as exc:
            if "outside of allowed window" not in exc.message.lower():
                if "could not reach" in exc.message.lower():
                    raise
                self._mark_failed(message, exc.message)
                return {"status": "failed"}
            try:
                result = self.client.send_text(connection.instagram_app_id, contact.platform_user_id, token, text, tag="HUMAN_AGENT")
            except InstagramApiError as tagged:
                if "could not reach" in tagged.message.lower():
                    raise
                self._mark_failed(message, "Instagram only accepts a reply within 24 hours of this person's last message.")
                return {"status": "failed"}
        message.external_message_id = str(result.get("message_id") or "") or None
        message.status = "sent"
        message.sent_at = datetime.now(timezone.utc)
        conversation.last_message_at = message.sent_at
        self.db.commit()
        return {"status": "sent"}

    def fail_send(self, message_id: uuid.UUID, reason: str) -> None:
        message = self.db.get(Message, message_id)
        if message is not None and message.status == "queued":
            self._mark_failed(message, reason)

    def conversation(self, tenant_id: uuid.UUID, conversation_id: uuid.UUID) -> dict[str, Any] | None:
        row = self.db.get(Conversation, conversation_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        contact = self.db.get(Contact, row.contact_id)
        messages = self.db.execute(
            select(Message).where(Message.conversation_id == row.id).order_by(Message.sent_at.asc().nullslast(), Message.created_at.asc())
        ).scalars()
        return {
            **self._conversation_public(row, contact, None),
            "messages": [self._message_public(item) for item in messages],
        }

    def _import_threads(self, connection: InstagramConnection, token: str, threads: list[dict[str, Any]]) -> dict[str, int]:
        account_id = uuid.UUID(str((connection.additional_attributes or {})["social_account_id"]))
        contacts = conversations = messages = 0
        for thread in threads:
            others = [person for person in thread.get("participants") or [] if not self._is_us(person, connection)]
            if not others or not thread.get("id"):
                continue
            contact, created = self._upsert_contact(connection, account_id, others[0], token)
            contacts += int(created)
            conversation, created = self._upsert_conversation(connection, account_id, contact, str(thread["id"]))
            conversations += int(created)
            latest: datetime | None = None
            for item in thread.get("messages") or []:
                sent_at = self._parse_time(item.get("created_time"))
                if self._upsert_message(connection, account_id, conversation, contact, item, sent_at):
                    messages += 1
                if sent_at and (latest is None or sent_at > latest):
                    latest = sent_at
            if latest:
                previous = self._aware(contact.last_interaction_at)
                contact.last_interaction_at = latest if previous is None or latest > previous else previous
                conversation.last_message_at = latest
        self.db.commit()
        return {"contacts": contacts, "conversations": conversations, "messages": messages}

    def _upsert_contact(self, connection: InstagramConnection, account_id: uuid.UUID, person: dict[str, Any], token: str) -> tuple[Contact, bool]:
        platform_user_id = str(person.get("id") or "")
        row = self.db.execute(
            select(Contact).where(Contact.social_account_id == account_id, Contact.platform_user_id == platform_user_id)
        ).scalars().first()
        created = row is None
        if row is None:
            row = Contact(tenant_id=connection.tenant_id, social_account_id=account_id, platform_user_id=platform_user_id, source="instagram_dm")
            self.db.add(row)
        profile = self.client.user_profile(platform_user_id, token) if platform_user_id else {}
        row.username = profile.get("username") or person.get("username") or row.username
        row.display_name = profile.get("name") or person.get("name") or row.username or row.display_name
        picture = profile.get("profile_pic") or person.get("profile_pic")
        stored = save_profile_picture(platform_user_id, picture) if picture else None
        if stored:
            row.profile_picture_url = stored
        extra = dict(row.custom_fields or {})
        for key in ("follower_count", "is_user_follow_business", "is_business_follow_user", "is_verified_user"):
            if profile.get(key) is not None:
                extra[key] = profile[key]
        extra["fetched_at"] = datetime.now(timezone.utc).isoformat()
        row.custom_fields = extra
        self.db.flush()
        return row, created

    def _refresh_account_profile(self, connection: InstagramConnection, token: str) -> None:
        try:
            profile = self.client.business_profile(connection.instagram_app_id, token)
        except InstagramApiError:
            return
        attrs = dict(connection.additional_attributes or {})
        if profile.get("username"):
            attrs["username"] = profile["username"]
        if profile.get("name"):
            attrs["name"] = profile["name"]
        stored = save_profile_picture(connection.instagram_app_id, profile.get("profile_picture_url") or "")
        if stored:
            attrs["profile_picture_url"] = stored
        connection.additional_attributes = attrs

    def _upsert_conversation(self, connection: InstagramConnection, account_id: uuid.UUID, contact: Contact, external_id: str) -> tuple[Conversation, bool]:
        row = self.db.execute(
            select(Conversation).where(Conversation.social_account_id == account_id, Conversation.external_conversation_id == external_id)
        ).scalars().first()
        created = row is None
        if row is None:
            row = Conversation(
                tenant_id=connection.tenant_id,
                social_account_id=account_id,
                contact_id=contact.id,
                external_conversation_id=external_id,
                status="open",
            )
            self.db.add(row)
            self.db.flush()
        return row, created

    def _upsert_message(
        self,
        connection: InstagramConnection,
        account_id: uuid.UUID,
        conversation: Conversation,
        contact: Contact,
        item: dict[str, Any],
        sent_at: datetime | None,
    ) -> bool:
        external_id = str(item.get("id") or "")
        if not external_id:
            return False
        existing = self.db.execute(
            select(Message.id).where(Message.social_account_id == account_id, Message.external_message_id == external_id)
        ).first()
        if existing:
            return False
        outbound = self._is_us(item.get("from") or {}, connection)
        text = (item.get("text") or "").strip()
        self.db.add(Message(
            tenant_id=connection.tenant_id,
            social_account_id=account_id,
            conversation_id=conversation.id,
            external_message_id=external_id,
            direction="outbound" if outbound else "inbound",
            sender_type="system" if outbound else "contact",
            sender_contact_id=None if outbound else contact.id,
            content=text or None,
            message_type="other" if item.get("is_unsupported") or not text else "text",
            status="received",
            sent_at=sent_at,
        ))
        self.db.flush()
        return True

    def _ensure_social_account(self, connection: InstagramConnection, user_id: uuid.UUID) -> SocialAccount:
        row = self.db.execute(
            select(SocialAccount).where(SocialAccount.platform == "instagram", SocialAccount.platform_account_id == connection.instagram_app_id)
        ).scalars().first()
        if row and row.tenant_id != connection.tenant_id:
            raise ConnectError("This Instagram account is already connected to another company.", status=409)
        attrs = connection.additional_attributes or {}
        if row is None:
            row = SocialAccount(
                tenant_id=connection.tenant_id,
                platform="instagram",
                platform_account_id=connection.instagram_app_id,
                status="connected",
                connected_by_user_id=user_id,
            )
            self.db.add(row)
        row.username = attrs.get("username") or row.username
        row.status = "connected"
        row.disconnected_at = None
        extra = dict(row.additional_attributes or {})
        extra.update({"name": attrs.get("name"), "profile_picture_url": attrs.get("profile_picture_url")})
        row.additional_attributes = extra
        self.db.flush()
        return row

    def _connection(self, tenant_id: uuid.UUID, connection_id: uuid.UUID) -> InstagramConnection:
        row = self.db.get(InstagramConnection, connection_id)
        if row is None or row.tenant_id != tenant_id or row.status != "connected":
            raise ConnectError("Instagram account not found.", status=404)
        return row

    def _set_status(self, connection: InstagramConnection, status: str, error: str | None) -> None:
        attrs = dict(connection.additional_attributes or {})
        attrs["sync_status"] = status
        attrs["sync_error"] = error
        if status == "synced":
            attrs["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        connection.additional_attributes = attrs
        self.db.commit()

    @staticmethod
    def _is_us(person: dict[str, Any], connection: InstagramConnection) -> bool:
        sender_id = str(person.get("id") or "")
        username = person.get("username")
        ours = (connection.additional_attributes or {}).get("username")
        return sender_id == connection.instagram_app_id or bool(username and ours and username == ours)

    @staticmethod
    def _parse_time(value: str | None) -> datetime | None:
        if not value:
            return None
        text = value.replace("Z", "+00:00")
        if text.endswith("+0000"):
            text = text[:-5] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return InstagramSyncService._aware(parsed)

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @staticmethod
    def _state(connection: InstagramConnection) -> dict[str, Any]:
        attrs = connection.additional_attributes or {}
        return {
            "id": connection.id,
            "instagram_app_id": connection.instagram_app_id,
            "username": attrs.get("username"),
            "name": attrs.get("name"),
            "profile_picture_url": attrs.get("profile_picture_url"),
            "contact_sync_enabled": bool(attrs.get("contact_sync_enabled")),
            "sync_status": attrs.get("sync_status") or "off",
            "sync_error": attrs.get("sync_error"),
            "last_synced_at": attrs.get("last_synced_at"),
        }

    def _latest_messages(self, conversation_ids: list[uuid.UUID]) -> dict[uuid.UUID, Message]:
        if not conversation_ids:
            return {}
        rows = self.db.execute(
            select(Message).where(Message.conversation_id.in_(conversation_ids)).order_by(Message.sent_at.desc().nullslast())
        ).scalars()
        found: dict[uuid.UUID, Message] = {}
        for row in rows:
            found.setdefault(row.conversation_id, row)
        return found

    @staticmethod
    def _contact_public(row: Contact) -> dict[str, Any]:
        return {
            "id": row.id,
            "platform_user_id": row.platform_user_id,
            "username": row.username,
            "display_name": row.display_name,
            "profile_picture_url": row.profile_picture_url,
            "source": row.source,
            "first_seen_at": row.first_seen_at,
            "last_interaction_at": row.last_interaction_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "fetched_at": (row.custom_fields or {}).get("fetched_at"),
            **InstagramSyncService._profile_facts(row.custom_fields),
        }

    @staticmethod
    def _conversation_public(row: Conversation, contact: Contact | None, preview: Message | None) -> dict[str, Any]:
        return {
            "id": row.id,
            "contact_id": row.contact_id,
            "contact_name": (contact.display_name if contact else None) or (contact.username if contact else None) or "Instagram user",
            "contact_username": contact.username if contact else None,
            "contact_profile_picture_url": contact.profile_picture_url if contact else None,
            "contact_platform_user_id": contact.platform_user_id if contact else None,
            **(InstagramSyncService._profile_facts(contact.custom_fields) if contact else {}),
            "status": row.status,
            "last_message_at": row.last_message_at,
            "last_message": preview.content if preview else None,
            "last_direction": preview.direction if preview else None,
        }

    @staticmethod
    def _profile_facts(fields: dict | None) -> dict[str, Any]:
        data = fields or {}
        return {
            "follower_count": data.get("follower_count"),
            "is_verified_user": bool(data.get("is_verified_user")),
            "follows_you": bool(data.get("is_user_follow_business")),
            "you_follow": bool(data.get("is_business_follow_user")),
        }

    def _mark_failed(self, message: Message, reason: str) -> None:
        message.status = "failed"
        extra = dict(message.additional_attributes or {})
        extra["send_error"] = reason[:500]
        message.additional_attributes = extra
        self.db.commit()

    @staticmethod
    def _message_public(row: Message) -> dict[str, Any]:
        return {
            "id": row.id,
            "direction": row.direction,
            "content": row.content,
            "message_type": row.message_type,
            "status": row.status,
            "send_error": (row.additional_attributes or {}).get("send_error"),
            "sent_at": row.sent_at,
        }
