"""Drop thread_id FK constraints on HITL tables + add admin role to messages.

Thread IDs in HITL sessions reference LangGraph checkpoint threads, not
application-level threads in the threads table. The FK constraints prevent
HITL session creation when the thread only exists in LangGraph's
AsyncPostgresSaver checkpoint tables.

Also adds 'admin' to the messages.role CHECK constraint for HITL messages
sent by admin users.

Revision ID: 005
Revises: 004
Create Date: 2026-04-05
"""

from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop FK constraints that reference threads(id) from HITL tables
    # These thread_ids come from LangGraph checkpointer, not the threads table
    op.execute(
        "ALTER TABLE hitl_sessions DROP CONSTRAINT IF EXISTS hitl_sessions_thread_id_fkey;"
    )
    op.execute(
        "ALTER TABLE hitl_escalation_tasks DROP CONSTRAINT IF EXISTS hitl_escalation_tasks_thread_id_fkey;"
    )

    # Add 'admin' role to messages CHECK constraint for HITL messages
    op.execute(
        "ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_role_check;"
    )
    op.execute(
        "ALTER TABLE messages ADD CONSTRAINT messages_role_check "
        "CHECK (role IN ('user', 'assistant', 'tool', 'system', 'admin'));"
    )


def downgrade() -> None:
    # Restore FK constraints
    op.execute(
        "ALTER TABLE hitl_sessions ADD CONSTRAINT hitl_sessions_thread_id_fkey "
        "FOREIGN KEY (thread_id) REFERENCES threads(id);"
    )
    op.execute(
        "ALTER TABLE hitl_escalation_tasks ADD CONSTRAINT hitl_escalation_tasks_thread_id_fkey "
        "FOREIGN KEY (thread_id) REFERENCES threads(id);"
    )

    # Restore original role CHECK
    op.execute(
        "ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_role_check;"
    )
    op.execute(
        "ALTER TABLE messages ADD CONSTRAINT messages_role_check "
        "CHECK (role IN ('user', 'assistant', 'tool', 'system'));"
    )
