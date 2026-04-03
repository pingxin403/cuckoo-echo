-- Cuckoo-Echo: Escalation & Tickets Migration
-- Adds tables referenced by HITL escalation code

-- ============================================================
-- hitl_escalation_tasks (delayed task queue for 60s escalation)
-- ============================================================
CREATE TABLE IF NOT EXISTS hitl_escalation_tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL REFERENCES hitl_sessions(id),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    thread_id   UUID NOT NULL REFERENCES threads(id),
    execute_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_escalation_tasks_execute_at ON hitl_escalation_tasks(execute_at);

-- ============================================================
-- tickets (created on auto-escalation)
-- ============================================================
CREATE TABLE IF NOT EXISTS tickets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    thread_id       UUID NOT NULL REFERENCES threads(id),
    hitl_session_id UUID REFERENCES hitl_sessions(id),
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
CREATE POLICY tickets_tenant_isolation ON tickets
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
