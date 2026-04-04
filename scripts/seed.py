"""Idempotent seed script for Cuckoo-Echo integration testing.

Creates test tenant, admin user, and default config.
All operations use ON CONFLICT DO NOTHING semantics.

Usage:
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import uuid

import asyncpg
import bcrypt


# ─── Seed Data ──────────────────────────────────────────────────

TENANT_ID = str(uuid.UUID("00000000-0000-4000-a000-000000000001"))
TENANT_NAME = "Integration Test Tenant"
API_KEY = "ck_test_integration_key"
API_KEY_HASH = hashlib.sha256(API_KEY.encode()).hexdigest()
API_KEY_PREFIX = API_KEY[:8]

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "test123456"
ADMIN_PASSWORD_HASH = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()

DEFAULT_LLM_CONFIG = {
    "system_prompt": "You are a helpful customer service assistant for integration testing.",
    "persona_name": "Test Bot",
    "model": os.environ.get("LLM_PRIMARY_MODEL", "ollama/qwen3:8b"),
    "fallback_model": os.environ.get("LLM_FALLBACK_MODEL", "ollama/qwen3:8b"),
    "temperature": 0.7,
}

DEFAULT_RATE_LIMIT = {
    "tenant_rps": 100,
    "user_rps": 10,
}


async def seed() -> None:
    """Create test data idempotently."""
    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cuckoo")
    conn = await asyncpg.connect(dsn)

    try:
        # 1. Create test tenant (ON CONFLICT DO NOTHING on api_key_hash unique constraint)
        await conn.execute(
            """
            INSERT INTO tenants (id, name, api_key_prefix, api_key_hash, status, llm_config, rate_limit, created_at)
            VALUES ($1::uuid, $2, $3, $4, 'active', $5::jsonb, $6::jsonb, NOW())
            ON CONFLICT (api_key_hash) DO NOTHING
            """,
            TENANT_ID,
            TENANT_NAME,
            API_KEY_PREFIX,
            API_KEY_HASH,
            __import__("json").dumps(DEFAULT_LLM_CONFIG),
            __import__("json").dumps(DEFAULT_RATE_LIMIT),
        )
        print(f"✅ Tenant: {TENANT_ID} ({TENANT_NAME})")
        print(f"   API Key: {API_KEY}")

        # 2. Create admin user (ON CONFLICT DO NOTHING on email unique constraint)
        await conn.execute(
            """
            INSERT INTO admin_users (tenant_id, email, password_hash, role, created_at)
            VALUES ($1::uuid, $2, $3, 'admin', NOW())
            ON CONFLICT (email) DO NOTHING
            """,
            TENANT_ID,
            ADMIN_EMAIL,
            ADMIN_PASSWORD_HASH,
        )
        print(f"✅ Admin User: {ADMIN_EMAIL}")

        print("\n🎉 Seed completed successfully!")
        print(f"   Tenant ID:  {TENANT_ID}")
        print(f"   API Key:    {API_KEY}")
        print(f"   Admin:      {ADMIN_EMAIL} / {ADMIN_PASSWORD}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
