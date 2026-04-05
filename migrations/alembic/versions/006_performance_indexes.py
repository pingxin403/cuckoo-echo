"""Add composite indexes for metrics and knowledge queries.

Revision ID: 006
Revises: 005
Create Date: 2026-04-05
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_threads_tenant_created "
        "ON threads(tenant_id, created_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_hitl_sessions_tenant_started "
        "ON hitl_sessions(tenant_id, started_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_docs_tenant_status "
        "ON knowledge_docs(tenant_id, status) WHERE deleted_at IS NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_threads_tenant_created;")
    op.execute("DROP INDEX IF EXISTS idx_hitl_sessions_tenant_started;")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_docs_tenant_status;")
