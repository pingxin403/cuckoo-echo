"""Idempotent seed script for Cuckoo-Echo integration testing.

Creates test tenant, API key, admin user, and default config.
All operations use IF NOT EXISTS / ON CONFLICT DO NOTHING semantics.

Usage:
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import hashlib
import os

import asyncpg
import bcrypt


# ─── Seed Data ──────────────────────────────────────────────────

TENANT_ID = "test-tenant-001"
TENANT_NAME = "Integration Test Tenant"
API_KEY = "ck_test_integration_key"
API_KEY_HASH = hashlib.sha256(API_KEY.encode()).hexdigest()

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "test123456"
ADMIN_PASSWORD_HASH = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()

DEFAULT_SYSTEM_PROMPT = "You are a helpful customer service assistant for integration testing."
DEFAULT_PERSONA_NAME = "Test Bot"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_FALLBACK_MODEL = "gpt-3.5-turbo"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TENANT_RPS = 100
DEFAULT_USER_RPS = 10


async def seed() -> None:
    """Create test data idempotently."""
    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cuckoo")
    conn = await asyncpg.connect(dsn)

    try:
        # 1. Create test tenant (IF NOT EXISTS)
        await conn.execute(
            """
            INSERT INTO tenants (tenant_id, name, created_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (tenant_id) DO NOTHING
            """,
            TENANT_ID,
            TENANT_NAME,
        )
        print(f"✅ Tenant: {TENANT_ID} ({TENANT_NAME})")

        # 2. Create API key (IF NOT EXISTS)
        await conn.execute(
            """
            INSERT INTO api_keys (tenant_id, key_hash, key_prefix, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (key_hash) DO NOTHING
            """,
            TENANT_ID,
            API_KEY_HASH,
            API_KEY[:8],
        )
        print(f"✅ API Key: {API_KEY[:8]}... (hash: {API_KEY_HASH[:16]}...)")

        # 3. Create admin user (IF NOT EXISTS)
        await conn.execute(
            """
            INSERT INTO admin_users (tenant_id, email, password_hash, role, created_at)
            VALUES ($1, $2, $3, 'admin', NOW())
            ON CONFLICT (email) DO NOTHING
            """,
            TENANT_ID,
            ADMIN_EMAIL,
            ADMIN_PASSWORD_HASH,
        )
        print(f"✅ Admin User: {ADMIN_EMAIL}")

        # 4. Initialize default LLM config (IF NOT EXISTS)
        await conn.execute(
            """
            INSERT INTO tenant_configs (tenant_id, config_key, config_value, updated_at)
            VALUES ($1, 'llm_config', $2::jsonb, NOW())
            ON CONFLICT (tenant_id, config_key) DO NOTHING
            """,
            TENANT_ID,
            f'{{"system_prompt": "{DEFAULT_SYSTEM_PROMPT}", "persona_name": "{DEFAULT_PERSONA_NAME}", '
            f'"model": "{DEFAULT_MODEL}", "fallback_model": "{DEFAULT_FALLBACK_MODEL}", '
            f'"temperature": {DEFAULT_TEMPERATURE}}}',
        )
        print("✅ Default LLM config")

        # 5. Initialize default rate limit config (IF NOT EXISTS)
        await conn.execute(
            """
            INSERT INTO tenant_configs (tenant_id, config_key, config_value, updated_at)
            VALUES ($1, 'rate_limit', $2::jsonb, NOW())
            ON CONFLICT (tenant_id, config_key) DO NOTHING
            """,
            TENANT_ID,
            f'{{"tenant_rps": {DEFAULT_TENANT_RPS}, "user_rps": {DEFAULT_USER_RPS}}}',
        )
        print("✅ Default rate limit config")

        print("\n🎉 Seed completed successfully!")
        print(f"   Tenant ID: {TENANT_ID}")
        print(f"   API Key:   {API_KEY}")
        print(f"   Admin:     {ADMIN_EMAIL} / {ADMIN_PASSWORD}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
