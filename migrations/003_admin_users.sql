CREATE TABLE admin_users (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id),
    email        TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin', 'super_admin')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY admin_users_tenant_isolation ON admin_users
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
