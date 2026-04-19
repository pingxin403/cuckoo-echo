"""Add billing tables — plans, accounts, usage_records, invoices.

Revision ID: 007
Revises: 006
Create Date: 2026-04-19 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE billing_plans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL UNIQUE,
            price DECIMAL NOT NULL,
            message_limit INTEGER NOT NULL DEFAULT -1,
            token_limit INTEGER NOT NULL DEFAULT -1,
            storage_mb INTEGER NOT NULL DEFAULT 1024,
            features JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE billing_accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            plan_id UUID REFERENCES billing_plans(id),
            balance DECIMAL NOT NULL DEFAULT 0,
            credit_limit DECIMAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active' 
                CHECK (status IN ('active', 'suspended', 'overdue')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE usage_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            period TEXT NOT NULL,
            messages_used INTEGER NOT NULL DEFAULT 0,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            tools_used INTEGER NOT NULL DEFAULT 0,
            storage_mb INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, period)
        );
    """)

    op.execute("""
        CREATE TABLE invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            amount DECIMAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'sent', 'paid', 'overdue')),
            period TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            paid_at TIMESTAMPTZ
        );
    """)

    op.execute("CREATE INDEX idx_billing_accounts_tenant ON billing_accounts(tenant_id);")
    op.execute("CREATE INDEX idx_usage_records_tenant_period ON usage_records(tenant_id, period);")
    op.execute("CREATE INDEX idx_invoices_tenant ON invoices(tenant_id);")

    op.execute("""
        INSERT INTO billing_plans (name, price, message_limit, token_limit, features) VALUES
        ('Free', 0, 100, 10000, '[]'),
        ('Starter', 49, 1000, 100000, '[]'),
        ('Pro', 199, 5000, 500000, '[]'),
        ('Enterprise', 0, -1, -1, '[]');
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS invoices CASCADE;")
    op.execute("DROP TABLE IF EXISTS usage_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS billing_accounts CASCADE;")
    op.execute("DROP TABLE IF EXISTS billing_plans CASCADE;")
