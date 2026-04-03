"""Thread memories — cross-thread long-term memory store.

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:00:03.000000

Wraps migrations/004_thread_memories.sql
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS thread_memories (
            tenant_id   UUID NOT NULL REFERENCES tenants(id),
            user_id     UUID NOT NULL REFERENCES users(id),
            key         TEXT NOT NULL,
            value       TEXT NOT NULL,
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (tenant_id, user_id, key)
        );

        ALTER TABLE thread_memories ENABLE ROW LEVEL SECURITY;
        CREATE POLICY thread_memories_tenant_isolation ON thread_memories
            USING (tenant_id = current_setting('app.current_tenant')::UUID);

        CREATE INDEX idx_thread_memories_user ON thread_memories(tenant_id, user_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS thread_memories CASCADE;")
