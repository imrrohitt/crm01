"""
Create invitations.

Only the SHA-256 hash of the invite token is stored.

Revision: 20261028_200010
"""

from alembic import op

revision = "20261028_200010"
down_revision = '20261028_200009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    email TEXT NOT NULL,
    role_id UUID,
    invited_by_user_id UUID,
    token_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_invitations_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_invitations_role FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE SET NULL,
    CONSTRAINT fk_invitations_invited_by FOREIGN KEY (invited_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT uq_invitations_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_invitations_email_lowercase CHECK (email = lower(btrim(email))),
    CONSTRAINT ck_invitations_status CHECK (status IN ('pending','accepted','revoked','expired'))
)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_invitations_pending_email ON invitations (tenant_id, email) WHERE status = 'pending'"""
    )

    op.execute(
        """CREATE INDEX ix_invitations_email ON invitations (email)"""
    )

    op.execute(
        """CREATE TRIGGER trg_invitations_set_updated_at BEFORE UPDATE ON invitations
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS invitations")
