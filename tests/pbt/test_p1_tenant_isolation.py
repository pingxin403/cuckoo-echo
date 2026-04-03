"""Property 1: Multi-tenant PostgreSQL data isolation.

# Feature: cuckoo-echo, Property 1: 多租户 PostgreSQL 数据隔离
**Validates: Requirements 1.3, 1.4, 1.7**

Structural property test — verifies that tenant_db_context always calls
SET LOCAL with the correct tenant_id, ensuring RLS activation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from hypothesis import given, settings, HealthCheck, assume, strategies as st

from shared.db import tenant_db_context


class _FakeTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(tenant_a_id=st.uuids(), tenant_b_id=st.uuids())
def test_rls_tenant_isolation(tenant_a_id, tenant_b_id):
    """SET LOCAL must always be called with the correct tenant_id for each context."""
    assume(tenant_a_id != tenant_b_id)
    loop = asyncio.new_event_loop()

    async def _check():
        conn = AsyncMock()
        conn.transaction = MagicMock(return_value=_FakeTx())

        # Query as tenant_a
        async with tenant_db_context(conn, str(tenant_a_id)):
            pass
        conn.execute.assert_awaited_with(
            "SET LOCAL app.current_tenant = $1", str(tenant_a_id)
        )

        # Query as tenant_b
        conn.reset_mock()
        conn.transaction = MagicMock(return_value=_FakeTx())
        async with tenant_db_context(conn, str(tenant_b_id)):
            pass
        conn.execute.assert_awaited_with(
            "SET LOCAL app.current_tenant = $1", str(tenant_b_id)
        )

    loop.run_until_complete(_check())
    loop.close()
