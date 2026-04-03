"""Escalation tables — hitl_escalation_tasks, tickets.

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:01.000000

Wraps migrations/002_escalation_tables.sql
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # hitl_escalation_tasks
    op.execute("""
        CREATE TABLE IF NOT EXISTS hitl_escalation_tasks (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id  UUID NOT NULL REFERENCES hitl_sessions(id),
            tenant_id   UUID NOT NULL REFERENCES tenants(id),
            thread_id   UUID NOT NULL REFERENCES threads(id),
            execute_at  TIMESTAMPTZ NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_escalation_tasks_execute_at "
        "ON hitl_escalation_tasks(execute_at);"
    )

    # tickets
    op.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            thread_id       UUID NOT NULL REFERENCES threads(id),
            hitl_session_id UUID REFERENCES hitl_sessions(id),
            status          TEXT NOT NULL DEFAULT 'open'
                            CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tickets_tenant_isolation ON tickets
            USING (tenant_id = current_setting('app.current_tenant')::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tickets CASCADE;")
    op.execute("DROP TABLE IF EXISTS hitl_escalation_tasks CASCADE;")
