"""Seed a test tenant with API key for development.

Usage:
    uv run python scripts/seed_tenant.py
    # or
    make seed
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import secrets

import asyncpg


async def main() -> None:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/cuckoo",
    )

    pool = await asyncpg.create_pool(database_url, statement_cache_size=0)
    assert pool is not None

    api_key = f"ck_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:10]

    async with pool.acquire() as conn:
        # Insert tenant (skip if already exists)
        existing = await conn.fetchrow(
            "SELECT id FROM tenants WHERE name = $1",
            "Test Tenant",
        )
        if existing:
            print(f"Test tenant already exists (id: {existing['id']})")
            print("To create a new API key, delete the existing tenant first.")
            await pool.close()
            return

        tenant_id = await conn.fetchval(
            "INSERT INTO tenants (name, api_key_prefix, api_key_hash) "
            "VALUES ($1, $2, $3) RETURNING id",
            "Test Tenant",
            key_prefix,
            key_hash,
        )

    print("=" * 60)
    print("Test tenant created successfully!")
    print(f"  Tenant ID:  {tenant_id}")
    print(f"  API Key:    {api_key}")
    print("=" * 60)
    print()
    print("Test with:")
    print(f'  curl -N http://localhost:8000/v1/chat/completions \\')
    print(f'    -H "Authorization: Bearer {api_key}" \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"user_id":"test_user","messages":[{{"role":"user","content":"hello"}}]}}\'')

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
