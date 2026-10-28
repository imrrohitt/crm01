"""
Create social_account_tokens.

Tokens are stored encrypted (application-level, key_version supports rotation). Never plain text.

Revision: 20261028_200020
"""

from alembic import op

revision = "20261028_200020"
down_revision = '20261028_200019'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE social_account_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    social_account_id UUID NOT NULL,
    access_token_encrypted BYTEA NOT NULL,
    refresh_token_encrypted BYTEA,
    key_version INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMPTZ,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_social_account_tokens_social_account FOREIGN KEY (social_account_id) REFERENCES social_accounts (id) ON DELETE CASCADE,
    CONSTRAINT uq_social_account_tokens_account UNIQUE (social_account_id)
)"""
    )

    op.execute(
        """CREATE INDEX ix_social_account_tokens_expires_at ON social_account_tokens (expires_at) WHERE expires_at IS NOT NULL"""
    )

    op.execute(
        """CREATE INDEX ix_social_account_tokens_scopes ON social_account_tokens USING GIN (scopes)"""
    )

    op.execute(
        """CREATE TRIGGER trg_social_account_tokens_set_updated_at BEFORE UPDATE ON social_account_tokens
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS social_account_tokens")
