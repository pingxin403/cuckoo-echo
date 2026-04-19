"""Unit tests for Admin HITL (Human-in-the-Loop) routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from admin_service.routes.hitl import (
    _poll_escalation_tasks,
    notify_hitl_request,
    router,
)


def _build_app(db_pool=None):
    """Build a test FastAPI app with the HITL router and fake auth middleware."""
    app = FastAPI()
    app.include_router(router)
    app.state.db_pool = db_pool or MagicMock()

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.tenant_id = "test-tenant"
        request.state.admin_user_id = "admin-001"
        return await call_next(request)

    return app


def _mock_pool(mock_conn=None):
    """Create a mock db_pool whose acquire() returns an async context manager."""
    conn = mock_conn or AsyncMock()
    pool = MagicMock()
    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=conn)
    acm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acm)
    return pool, conn


class TestTakeSession:
    """POST /admin/v1/hitl/{session_id}/take"""

    def test_take_sets_thread_to_human_intervention(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={
            "thread_id": "thread-abc",
            "status": "pending",
        })
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.hitl.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.post("/admin/v1/hitl/session-123/take")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "active"
        assert body["thread_id"] == "thread-abc"

        # Verify thread was set to human_intervention
        execute_calls = conn.execute.await_args_list
        thread_update = [c for c in execute_calls if "human_intervention" in str(c)]
        assert len(thread_update) == 1

        # Verify hitl_session was set to active
        session_update = [c for c in execute_calls if "status = 'active'" in str(c)]
        assert len(session_update) == 1

    def test_take_returns_404_for_missing_session(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.hitl.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.post("/admin/v1/hitl/nonexistent/take")

        assert resp.status_code == 404

    def test_take_returns_409_if_already_active(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={
            "thread_id": "thread-abc",
            "status": "active",
        })
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.hitl.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.post("/admin/v1/hitl/session-123/take")

        assert resp.status_code == 409


class TestEndSession:
    """POST /admin/v1/hitl/{session_id}/end"""

    def test_end_restores_thread_to_active(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={
            "thread_id": "thread-abc",
            "status": "active",
        })
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.hitl.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.post("/admin/v1/hitl/session-123/end")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "resolved"
        assert body["thread_id"] == "thread-abc"

        # Verify thread was restored to active
        execute_calls = conn.execute.await_args_list
        thread_update = [c for c in execute_calls if "status = 'active'" in str(c) and "threads" in str(c)]
        assert len(thread_update) == 1

        # Verify hitl_session was set to resolved with ended_at
        session_update = [c for c in execute_calls if "'resolved'" in str(c)]
        assert len(session_update) == 1
        assert "ended_at = NOW()" in str(session_update[0])

    def test_end_returns_404_for_missing_session(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.hitl.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.post("/admin/v1/hitl/nonexistent/end")

        assert resp.status_code == 404

    def test_end_returns_409_if_not_active(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={
            "thread_id": "thread-abc",
            "status": "pending",
        })
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.hitl.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.post("/admin/v1/hitl/session-123/end")

        assert resp.status_code == 409


class TestNotifyHitlRequest:
    """notify_hitl_request inserts session + escalation task."""

    @pytest.mark.asyncio
    async def test_creates_session_and_escalation_task(self):
        conn = AsyncMock()
        pool, _ = _mock_pool(conn)

        with patch("admin_service.routes.hitl.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            with patch("admin_service.routes.hitl.broadcast_to_tenant", new_callable=AsyncMock) as mock_broadcast:
                session_id = await notify_hitl_request(
                    pool, "tenant-1", "thread-1", reason="negative_sentiment", unresolved_turns=3,
                )

        assert session_id  # non-empty string

        # Verify two INSERT calls: hitl_sessions + hitl_escalation_tasks
        execute_calls = conn.execute.await_args_list
        insert_calls = [c for c in execute_calls if "INSERT" in str(c)]
        assert len(insert_calls) == 2

        session_insert = [c for c in insert_calls if "hitl_sessions" in str(c)]
        assert len(session_insert) == 1

        escalation_insert = [c for c in insert_calls if "hitl_escalation_tasks" in str(c)]
        assert len(escalation_insert) == 1
        assert "60 seconds" in str(escalation_insert[0])

        # Verify WS broadcast was called
        mock_broadcast.assert_awaited_once()
        call_payload = mock_broadcast.await_args[0][1]
        assert call_payload["type"] == "hitl_request"
        assert call_payload["thread_id"] == "thread-1"


class TestEscalationPoller:
    """_poll_escalation_tasks processes overdue tasks."""

    @pytest.mark.asyncio
    async def test_escalation_sets_auto_escalated_and_creates_ticket(self):
        """When a pending session has an overdue escalation task, it should
        be auto-escalated and a ticket should be created."""
        conn = AsyncMock()

        # First fetchrow: the escalation task row
        # Second fetchrow: the session status check
        conn.fetchrow = AsyncMock(side_effect=[
            {
                "id": "task-1",
                "session_id": "session-1",
                "tenant_id": "tenant-1",
                "thread_id": "thread-1",
            },
            {"status": "pending"},
        ])

        # Mock transaction context manager
        tx_cm = AsyncMock()
        tx_cm.__aenter__ = AsyncMock(return_value=None)
        tx_cm.__aexit__ = AsyncMock(return_value=False)
        conn.transaction = MagicMock(return_value=tx_cm)

        pool, _ = _mock_pool(conn)

        await _poll_escalation_tasks(pool)

        execute_calls = conn.execute.await_args_list

        # Should have: UPDATE hitl_sessions (auto_escalated), INSERT ticket, DELETE task
        escalate_update = [c for c in execute_calls if "auto_escalated" in str(c)]
        assert len(escalate_update) == 1

        ticket_insert = [c for c in execute_calls if "INSERT INTO tickets" in str(c)]
        assert len(ticket_insert) == 1

        task_delete = [c for c in execute_calls if "DELETE FROM hitl_escalation_tasks" in str(c)]
        assert len(task_delete) == 1

    @pytest.mark.asyncio
    async def test_escalation_skips_if_session_already_taken(self):
        """If admin already took the session, escalation should just delete the task."""
        conn = AsyncMock()

        conn.fetchrow = AsyncMock(side_effect=[
            {
                "id": "task-1",
                "session_id": "session-1",
                "tenant_id": "tenant-1",
                "thread_id": "thread-1",
            },
            {"status": "active"},  # Already taken by admin
        ])

        tx_cm = AsyncMock()
        tx_cm.__aenter__ = AsyncMock(return_value=None)
        tx_cm.__aexit__ = AsyncMock(return_value=False)
        conn.transaction = MagicMock(return_value=tx_cm)

        pool, _ = _mock_pool(conn)

        await _poll_escalation_tasks(pool)

        execute_calls = conn.execute.await_args_list

        # Should NOT escalate or create ticket
        escalate_update = [c for c in execute_calls if "auto_escalated" in str(c)]
        assert len(escalate_update) == 0

        ticket_insert = [c for c in execute_calls if "INSERT INTO tickets" in str(c)]
        assert len(ticket_insert) == 0

        # Should still delete the task
        task_delete = [c for c in execute_calls if "DELETE FROM hitl_escalation_tasks" in str(c)]
        assert len(task_delete) == 1

    @pytest.mark.asyncio
    async def test_no_op_when_no_overdue_tasks(self):
        """When there are no overdue tasks, nothing happens."""
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)

        tx_cm = AsyncMock()
        tx_cm.__aenter__ = AsyncMock(return_value=None)
        tx_cm.__aexit__ = AsyncMock(return_value=False)
        conn.transaction = MagicMock(return_value=tx_cm)

        pool, _ = _mock_pool(conn)

        await _poll_escalation_tasks(pool)

        # No execute calls beyond the initial fetchrow
        conn.execute.assert_not_awaited()
