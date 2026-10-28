"""
Create messages.

Full-text search via GIN on to_tsvector. (social_account_id, external_message_id) makes webhook retries idempotent.

Revision: 20261028_200025
"""

from alembic import op

revision = "20261028_200025"
down_revision = '20261028_200024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    external_message_id TEXT,
    direction TEXT NOT NULL,
    sender_type TEXT NOT NULL,
    sender_contact_id UUID,
    sender_membership_id UUID,
    content TEXT,
    message_type TEXT NOT NULL DEFAULT 'text',
    media_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'received',
    sent_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_messages_conversation FOREIGN KEY (tenant_id, social_account_id, conversation_id) REFERENCES conversations (tenant_id, social_account_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_messages_sender_contact FOREIGN KEY (tenant_id, sender_contact_id) REFERENCES contacts (tenant_id, id),
    CONSTRAINT fk_messages_sender_membership FOREIGN KEY (tenant_id, sender_membership_id) REFERENCES tenant_memberships (tenant_id, id),
    CONSTRAINT uq_messages_account_external UNIQUE (social_account_id, external_message_id),
    CONSTRAINT uq_messages_tenant_id_id UNIQUE (tenant_id, id),
    CONSTRAINT ck_messages_direction CHECK (direction IN ('inbound','outbound')),
    CONSTRAINT ck_messages_sender_type CHECK (sender_type IN ('contact','agent','automation','system')),
    CONSTRAINT ck_messages_direction_matches_sender CHECK ((direction = 'inbound') = (sender_type = 'contact')),
    CONSTRAINT ck_messages_sender_ids CHECK (
        (sender_type = 'contact' AND sender_contact_id IS NOT NULL AND sender_membership_id IS NULL)
     OR (sender_type = 'agent' AND sender_membership_id IS NOT NULL AND sender_contact_id IS NULL)
     OR (sender_type IN ('automation','system') AND sender_contact_id IS NULL AND sender_membership_id IS NULL)),
    CONSTRAINT ck_messages_type CHECK (message_type IN ('text','image','video','audio','story_reply','reaction','share','other')),
    CONSTRAINT ck_messages_status CHECK (status IN ('received','queued','sent','delivered','read','failed'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_messages_conversation_sent ON messages (tenant_id, conversation_id, sent_at)"""
    )

    op.execute(
        """CREATE INDEX ix_messages_content_fts ON messages USING GIN (to_tsvector('simple', coalesce(content, '')))"""
    )

    op.execute(
        """CREATE INDEX ix_messages_media_metadata ON messages USING GIN (media_metadata jsonb_path_ops)"""
    )

    op.execute(
        """CREATE INDEX ix_messages_pending_send ON messages (created_at) WHERE status = 'queued'"""
    )

    op.execute(
        """CREATE TRIGGER trg_messages_set_updated_at BEFORE UPDATE ON messages
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS messages")
