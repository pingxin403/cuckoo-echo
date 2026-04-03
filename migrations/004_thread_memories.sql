-- Cross-thread long-term memory store
-- Stores user preferences and context accessible across all threads

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
