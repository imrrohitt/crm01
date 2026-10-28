"""
Create ai_usage_records.

Revision: 20261028_200034
"""

from alembic import op

revision = "20261028_200034"
down_revision = '20261028_200033'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE ai_usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost NUMERIC(12,6) NOT NULL DEFAULT 0,
    request_id TEXT,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_ai_usage_records_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_ai_usage_records_conversation FOREIGN KEY (tenant_id, conversation_id) REFERENCES conversations (tenant_id, id) ON DELETE SET NULL (conversation_id),
    CONSTRAINT ck_ai_usage_records_tokens CHECK (input_tokens >= 0 AND output_tokens >= 0 AND estimated_cost >= 0)
)"""
    )

    op.execute(
        """CREATE INDEX ix_ai_usage_records_tenant_created ON ai_usage_records (tenant_id, created_at DESC)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_ai_usage_records_request ON ai_usage_records (tenant_id, request_id) WHERE request_id IS NOT NULL"""
    )

    op.execute(
        """CREATE TRIGGER trg_ai_usage_records_set_updated_at BEFORE UPDATE ON ai_usage_records
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_usage_records")
