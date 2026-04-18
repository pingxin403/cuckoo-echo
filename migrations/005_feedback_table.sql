-- Cuckoo-Echo: Feedback Table Migration
-- Adds feedback table with multi-tenant isolation and Langfuse correlation

-- Enable pgcrypto for gen_random_uuid() if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- feedback (user feedback loop)
-- ============================================================
CREATE TABLE IF NOT EXISTS feedback (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id           UUID NOT NULL,
    message_id          UUID NOT NULL,
    user_id             UUID NOT NULL,
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    feedback_type       TEXT NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Multi-tenant isolation
    partition_key       VARCHAR(255) NOT NULL,
    
    -- Langfuse correlation
    langfuse_trace_id   UUID,
    langfuse_span_id    UUID
);

-- RLS Policy for multi-tenant isolation
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
CREATE POLICY feedback_tenant_isolation ON feedback
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_feedback_tenant ON feedback (tenant_id);
CREATE INDEX IF NOT EXISTS idx_feedback_thread ON feedback (thread_id);
CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback (message_id);
CREATE INDEX IF NOT EXISTS idx_feedback_partition ON feedback (partition_key);
CREATE INDEX IF NOT EXISTS idx_feedback_thread_message ON feedback (thread_id, message_id);

-- Unique constraint to prevent duplicate feedback for same message
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_unique ON feedback (thread_id, message_id, user_id, tenant_id);
