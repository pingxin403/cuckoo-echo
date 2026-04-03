"""Initial schema — tenants, users, threads, messages, knowledge_docs, hitl_sessions.

Revision ID: 001
Revises: None
Create Date: 2024-01-01 00:00:00.000000

Wraps migrations/001_initial.sql
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # tenants
    op.execute("""
        CREATE TABLE tenants (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT NOT NULL,
            api_key_prefix  TEXT NOT NULL,
            api_key_hash    TEXT NOT NULL UNIQUE,
            status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
            llm_config      JSONB NOT NULL DEFAULT '{}',
            rate_limit      JSONB NOT NULL DEFAULT '{"tenant_rps": 100, "user_rps": 10}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX idx_tenants_api_key_hash ON tenants(api_key_hash);")

    # users
    op.execute("""
        CREATE TABLE users (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID NOT NULL REFERENCES tenants(id),
            external_uid TEXT NOT NULL,
            profile      JSONB NOT NULL DEFAULT '{}',
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, external_uid)
        );
    """)
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY users_tenant_isolation ON users
            USING (tenant_id = current_setting('app.current_tenant')::UUID);
    """)

    # threads
    op.execute("""
        CREATE TABLE threads (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL REFERENCES tenants(id),
            user_id     UUID NOT NULL REFERENCES users(id),
            title       TEXT,
            status      TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'human_intervention', 'closed')),
            metadata    JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("ALTER TABLE threads ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY threads_tenant_isolation ON threads
            USING (tenant_id = current_setting('app.current_tenant')::UUID);
    """)
    op.execute("CREATE INDEX idx_threads_tenant_user ON threads(tenant_id, user_id);")

    # messages
    op.execute("""
        CREATE TABLE messages (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID NOT NULL REFERENCES tenants(id),
            thread_id    UUID NOT NULL REFERENCES threads(id),
            role         TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
            content      TEXT,
            media_urls   JSONB NOT NULL DEFAULT '[]',
            tool_calls   JSONB NOT NULL DEFAULT '[]',
            tokens_used  INTEGER NOT NULL DEFAULT 0,
            status       TEXT NOT NULL DEFAULT 'completed'
                         CHECK (status IN ('completed', 'interrupted', 'streaming')),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY messages_tenant_isolation ON messages
            USING (tenant_id = current_setting('app.current_tenant')::UUID);
    """)
    op.execute("CREATE INDEX idx_messages_thread ON messages(thread_id, created_at);")
    op.execute("CREATE INDEX idx_messages_tenant ON messages(tenant_id, created_at);")

    # knowledge_docs
    op.execute("""
        CREATE TABLE knowledge_docs (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL REFERENCES tenants(id),
            filename    TEXT NOT NULL,
            oss_path    TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
            chunk_count INTEGER,
            error_msg   TEXT,
            deleted_at  TIMESTAMPTZ,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("ALTER TABLE knowledge_docs ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY knowledge_docs_tenant_isolation ON knowledge_docs
            USING (tenant_id = current_setting('app.current_tenant')::UUID);
    """)

    # hitl_sessions
    op.execute("""
        CREATE TABLE hitl_sessions (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID NOT NULL REFERENCES tenants(id),
            thread_id     UUID NOT NULL REFERENCES threads(id),
            admin_user_id UUID,
            started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at      TIMESTAMPTZ,
            status        TEXT NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending', 'active', 'resolved', 'auto_escalated'))
        );
    """)
    op.execute("ALTER TABLE hitl_sessions ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY hitl_sessions_tenant_isolation ON hitl_sessions
            USING (tenant_id = current_setting('app.current_tenant')::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hitl_sessions CASCADE;")
    op.execute("DROP TABLE IF EXISTS knowledge_docs CASCADE;")
    op.execute("DROP TABLE IF EXISTS messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS threads CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE;")
