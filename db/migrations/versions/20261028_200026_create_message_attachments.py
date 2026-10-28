"""
Create message_attachments.

Revision: 20261028_200026
"""

from alembic import op

revision = "20261028_200026"
down_revision = '20261028_200025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE message_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    message_id UUID NOT NULL,
    media_type TEXT NOT NULL,
    media_url TEXT,
    external_media_id TEXT,
    mime_type TEXT,
    size_bytes BIGINT,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_message_attachments_message FOREIGN KEY (tenant_id, message_id) REFERENCES messages (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT ck_message_attachments_size CHECK (size_bytes IS NULL OR size_bytes >= 0)
)"""
    )

    op.execute(
        """CREATE INDEX ix_message_attachments_message ON message_attachments (message_id)"""
    )

    op.execute(
        """CREATE TRIGGER trg_message_attachments_set_updated_at BEFORE UPDATE ON message_attachments
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS message_attachments")
