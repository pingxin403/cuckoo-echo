"""Admin users table.

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:02.000000

Wraps migrations/003_admin_users.sql
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE admin_users (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID NOT NULL REFERENCES tenants(id),
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'admin'
                          CHECK (role IN ('admin', 'super_admin')),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY admin_users_tenant_isolation ON admin_users
            USING (tenant_id = current_setting('app.current_tenant')::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin_users CASCADE;")
