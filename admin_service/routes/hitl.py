"""Admin HITL (Human-in-the-Loop) API routes."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect

from shared.db import tenant_db_context

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1")

# ---------------------------------------------------------------------------
# Per-tenant WebSocket connection registry
# ---------------------------------------------------------------------------
_ws_connections: dict[str, list[WebSocket]] = defaultdict(list)


async def broadcast_to_tenant(tenant_id: str, payload: dict) -> None:
    """Push a JSON message to all WebSocket connections for a tenant."""
    dead: list[WebSocket] = []
    for ws in _ws_connections.get(tenant_id, []):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_connections[tenant_id].remove(ws)


@router.websocket("/ws/hitl")
async def hitl_websocket(websocket: WebSocket):
    """Maintain a per-tenant WebSocket connection for HITL events.

    The client must send an initial JSON message with ``{"tenant_id": "..."}``
    to register itself.  After that the server pushes HITL request events.
    """
    await websocket.accept()
    tenant_id: str | None = None
    try:
        # Expect an initial registration message
        init_msg = await websocket.receive_json()
        tenant_id = init_msg.get("tenant_id")
        if not tenant_id:
            await websocket.close(code=4001, reason="tenant_id required")
            return
        _ws_connections[tenant_id].append(websocket)
        log.info("hitl_ws_connected", tenant_id=tenant_id)

        # Keep connection alive — wait for client messages (ping/pong or close)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if tenant_id and websocket in _ws_connections.get(tenant_id, []):
            _ws_connections[tenant_id].remove(websocket)
            log.info("hitl_ws_disconnected", tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Notify HITL — called when agent sets hitl_requested=True
# ---------------------------------------------------------------------------

async def notify_hitl_request(
    db_pool,
    tenant_id: str,
    thread_id: str,
    reason: str = "",
    unresolved_turns: int = 0,
) -> str:
    """Create a pending hitl_session, insert an escalation task, and push WS event.

    Returns the new session id.
    """
    session_id = str(uuid4())

    async with db_pool.acquire() as conn:
        # Ensure a system user exists for this tenant
        system_user_id = tenant_id
        await conn.execute(
            """INSERT INTO users (id, tenant_id, external_uid)
               VALUES ($1::uuid, $2::uuid, 'system')
               ON CONFLICT (tenant_id, external_uid) DO NOTHING""",
            system_user_id, tenant_id,
        )
        # All subsequent INSERTs need RLS context (app.current_tenant)
        async with tenant_db_context(conn, tenant_id):
            # Ensure thread row exists (FK constraint on hitl_sessions.thread_id)
            await conn.execute(
                """INSERT INTO threads (id, tenant_id, user_id, status)
                   VALUES ($1::uuid, $2::uuid, $3::uuid, 'human_intervention')
                   ON CONFLICT (id) DO NOTHING""",
                thread_id, tenant_id, system_user_id,
            )
            await conn.execute(
                """INSERT INTO hitl_sessions (id, tenant_id, thread_id, status)
                   VALUES ($1::uuid, $2::uuid, $3::uuid, 'pending')""",
                session_id, tenant_id, thread_id,
            )
            await conn.execute(
                """INSERT INTO hitl_escalation_tasks
                       (id, session_id, tenant_id, thread_id, execute_at)
                   VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, NOW() + INTERVAL '60 seconds')""",
                str(uuid4()), session_id, tenant_id, thread_id,
            )
            await conn.execute(
                """INSERT INTO hitl_sessions (id, tenant_id, thread_id, status)
                   VALUES ($1::uuid, $2::uuid, $3::uuid, 'pending')""",
                session_id, tenant_id, thread_id,
            )
            await conn.execute(
                """INSERT INTO hitl_escalation_tasks
                       (id, session_id, tenant_id, thread_id, execute_at)
                   VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, NOW() + INTERVAL '60 seconds')""",
                str(uuid4()), session_id, tenant_id, thread_id,
            )

    # Push event to admin WebSocket connections
    await broadcast_to_tenant(tenant_id, {
        "type": "hitl_request",
        "session_id": session_id,
        "thread_id": thread_id,
        "reason": reason,
        "unresolved_turns": unresolved_turns,
    })

    log.info("hitl_request_created", session_id=session_id, tenant_id=tenant_id, thread_id=thread_id)
    return session_id


# ---------------------------------------------------------------------------
# GET /admin/v1/hitl/sessions — list HITL sessions for tenant
# ---------------------------------------------------------------------------

@router.get("/hitl/sessions")
async def list_sessions(request: Request):
    """List HITL sessions for the authenticated tenant."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            rows = await conn.fetch(
                """SELECT id AS session_id, thread_id, status, admin_user_id,
                          created_at, ended_at
                   FROM hitl_sessions
                   WHERE tenant_id = $1
                   ORDER BY created_at DESC
                   LIMIT 50""",
                tenant_id,
            )

    return [
        {
            "session_id": str(row["session_id"]),
            "thread_id": str(row["thread_id"]),
            "status": row["status"],
            "admin_user_id": str(row["admin_user_id"]) if row["admin_user_id"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# POST /admin/v1/hitl/{session_id}/take
# ---------------------------------------------------------------------------

@router.post("/hitl/{session_id}/take")
async def take_session(session_id: str, request: Request):
    """Admin takes over a HITL session — sets thread to human_intervention."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id
    admin_user_id = getattr(request.state, "admin_user_id", str(uuid4()))

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            row = await conn.fetchrow(
                "SELECT thread_id, status FROM hitl_sessions WHERE id = $1",
                session_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Session not found")
            if row["status"] not in ("pending",):
                raise HTTPException(status_code=409, detail=f"Session already {row['status']}")

            thread_id = row["thread_id"]

            # Update thread status
            await conn.execute(
                "UPDATE threads SET status = 'human_intervention', updated_at = NOW() WHERE id = $1",
                thread_id,
            )
            # Update hitl_session
            await conn.execute(
                "UPDATE hitl_sessions SET admin_user_id = $1, status = 'active' WHERE id = $2",
                admin_user_id, session_id,
            )

    log.info("hitl_session_taken", session_id=session_id, admin_user_id=admin_user_id)
    return {"session_id": session_id, "thread_id": thread_id, "status": "active"}


# ---------------------------------------------------------------------------
# POST /admin/v1/hitl/{session_id}/end
# ---------------------------------------------------------------------------

@router.post("/hitl/{session_id}/end")
async def end_session(session_id: str, request: Request):
    """Admin ends a HITL session — restores thread to active."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            row = await conn.fetchrow(
                "SELECT thread_id, status FROM hitl_sessions WHERE id = $1",
                session_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Session not found")
            if row["status"] not in ("active",):
                raise HTTPException(status_code=409, detail=f"Session is {row['status']}, not active")

            thread_id = row["thread_id"]

            # Restore thread status
            await conn.execute(
                "UPDATE threads SET status = 'active', updated_at = NOW() WHERE id = $1",
                thread_id,
            )
            # Close hitl_session
            await conn.execute(
                "UPDATE hitl_sessions SET ended_at = NOW(), status = 'resolved' WHERE id = $1",
                session_id,
            )

    log.info("hitl_session_ended", session_id=session_id)
    return {"session_id": session_id, "thread_id": thread_id, "status": "resolved"}


# ---------------------------------------------------------------------------
# POST /admin/v1/hitl/{session_id}/message — admin sends message in HITL
# ---------------------------------------------------------------------------

@router.post("/hitl/{session_id}/message")
async def send_hitl_message(session_id: str, request: Request):
    """Admin sends a message in an active HITL session."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id
    body = await request.json()
    content = body.get("content", "").strip()

    if not content:
        raise HTTPException(status_code=400, detail="Message content is required")

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            row = await conn.fetchrow(
                "SELECT thread_id, status FROM hitl_sessions WHERE id = $1",
                session_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Session not found")
            if row["status"] != "active":
                raise HTTPException(status_code=409, detail=f"Session is {row['status']}, not active")

            thread_id = row["thread_id"]
            message_id = str(uuid4())
            now = datetime.now(timezone.utc)

            await conn.execute(
                """INSERT INTO messages (id, thread_id, role, content, created_at)
                   VALUES ($1, $2, 'admin', $3, $4)""",
                message_id, thread_id, content, now,
            )

    log.info("hitl_message_sent", session_id=session_id, message_id=message_id)
    return {
        "id": message_id,
        "thread_id": thread_id,
        "role": "admin",
        "content": content,
        "created_at": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# 60s Escalation Timer — background polling loop
# ---------------------------------------------------------------------------

async def run_escalation_poller(db_pool, poll_interval: float = 5.0) -> None:
    """Background loop that checks for overdue escalation tasks.

    Uses SELECT FOR UPDATE SKIP LOCKED for multi-worker safety.
    Runs until cancelled.
    """
    log.info("escalation_poller_started")
    while True:
        try:
            await _poll_escalation_tasks(db_pool)
        except asyncio.CancelledError:
            log.info("escalation_poller_stopped")
            raise
        except Exception:
            log.exception("escalation_poller_error")
        await asyncio.sleep(poll_interval)


async def _poll_escalation_tasks(db_pool) -> None:
    """Process one batch of overdue escalation tasks."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """SELECT id, session_id, tenant_id, thread_id
                   FROM hitl_escalation_tasks
                   WHERE execute_at <= NOW()
                   ORDER BY execute_at
                   LIMIT 1
                   FOR UPDATE SKIP LOCKED"""
            )
            if not row:
                return

            task_id = row["id"]
            session_id = row["session_id"]
            tenant_id = row["tenant_id"]
            thread_id = row["thread_id"]

            # Check if session is still pending (admin may have taken it already)
            session = await conn.fetchrow(
                "SELECT status FROM hitl_sessions WHERE id = $1",
                session_id,
            )
            if session and session["status"] == "pending":
                # Escalate: update session status
                await conn.execute(
                    "UPDATE hitl_sessions SET status = 'auto_escalated' WHERE id = $1",
                    session_id,
                )
                # Create a ticket row
                ticket_id = str(uuid4())
                await conn.execute(
                    """INSERT INTO tickets (id, tenant_id, thread_id, hitl_session_id, status)
                       VALUES ($1, $2, $3, $4, 'open')""",
                    ticket_id, tenant_id, thread_id, session_id,
                )
                log.info(
                    "hitl_escalated",
                    session_id=session_id,
                    ticket_id=ticket_id,
                    tenant_id=tenant_id,
                )

            # Delete the processed task
            await conn.execute(
                "DELETE FROM hitl_escalation_tasks WHERE id = $1",
                task_id,
            )
