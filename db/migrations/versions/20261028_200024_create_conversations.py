"""
Create conversations.

Composite FK guarantees contact, social account and conversation all belong to the same tenant.

Revision: 20261028_200024
"""

from alembic import op

revision = "20261028_200024"
down_revision = '20261028_200023'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    contact_id UUID NOT NULL,
    external_conversation_id TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'normal',
    last_message_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_conversations_contact FOREIGN KEY (tenant_id, social_account_id, contact_id) REFERENCES contacts (tenant_id, social_account_id, id) ON DELETE CASCADE,
    CONSTRAINT uq_conversations_tenant_id_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_conversations_tenant_account_id UNIQUE (tenant_id, social_account_id, id),
    CONSTRAINT ck_conversations_status CHECK (status IN ('open','pending','resolved')),
    CONSTRAINT ck_conversations_priority CHECK (priority IN ('low','normal','high'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_conversations_inbox ON conversations (tenant_id, status, last_message_at DESC NULLS LAST)"""
    )

    op.execute(
        """CREATE INDEX ix_conversations_contact ON conversations (contact_id)"""
    )

    op.execute(
        """CREATE INDEX ix_conversations_account ON conversations (social_account_id)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_conversations_external ON conversations (social_account_id, external_conversation_id) WHERE external_conversation_id IS NOT NULL"""
    )

    op.execute(
        """CREATE INDEX ix_conversations_additional_attributes ON conversations USING GIN (additional_attributes jsonb_path_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_conversations_set_updated_at BEFORE UPDATE ON conversations
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS conversations")
