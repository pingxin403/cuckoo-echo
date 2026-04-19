"""Admin Billing API — plans, usage, invoices."""
from __future__ import annotations

import orjson
import structlog
from asyncpg import Pool
from fastapi import APIRouter, Request
from pydantic import BaseModel

from shared.billing import DEFAULT_PLANS

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1/billing")


class PlanCreate(BaseModel):
    name: str
    price: int
    message_limit: int
    token_limit: int
    features: dict | None = None


class PlanUpdate(BaseModel):
    name: str | None = None
    price: int | None = None
    message_limit: int | None = None
    token_limit: int | None = None
    features: dict | None = None


class InvoiceCreate(BaseModel):
    tenant_id: str
    amount: int
    period: str
    status: str = "pending"


@router.get("/plans")
async def list_plans(request: Request):
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, price, message_limit, token_limit, features, created_at
            FROM billing_plans ORDER BY price ASC
            """
        )
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "price": r["price"],
            "message_limit": r["message_limit"],
            "token_limit": r["token_limit"],
            "features": r["features"] or {},
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@router.post("/plans")
async def create_plan(body: PlanCreate, request: Request):
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO billing_plans (name, price, message_limit, token_limit, features)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            body.name,
            body.price,
            body.message_limit,
            body.token_limit,
            orjson.dumps(body.features).decode() if body.features else None,
        )
    log.info("billing_plan_created", plan_id=str(row["id"]), name=body.name)
    return {"id": str(row["id"]), "created": True}


@router.put("/plans/{plan_id}")
async def update_plan(plan_id: str, body: PlanUpdate, request: Request):
    db_pool = request.app.state.db_pool
    updates = []
    params = [plan_id]
    param_idx = 2

    if body.name is not None:
        updates.append(f"name = ${param_idx}")
        params.append(body.name)
        param_idx += 1
    if body.price is not None:
        updates.append(f"price = ${param_idx}")
        params.append(body.price)
        param_idx += 1
    if body.message_limit is not None:
        updates.append(f"message_limit = ${param_idx}")
        params.append(body.message_limit)
        param_idx += 1
    if body.token_limit is not None:
        updates.append(f"token_limit = ${param_idx}")
        params.append(body.token_limit)
        param_idx += 1
    if body.features is not None:
        updates.append(f"features = ${param_idx}")
        params.append(orjson.dumps(body.features).decode())
        param_idx += 1

    if not updates:
        return {"updated": False, "reason": "no fields to update"}

    async with db_pool.acquire() as conn:
        await conn.execute(
            f"UPDATE billing_plans SET {', '.join(updates)} WHERE id = $1",
            *params,
        )
    log.info("billing_plan_updated", plan_id=plan_id)
    return {"updated": True}


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, request: Request):
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM billing_plans WHERE id = $1", plan_id)
    log.info("billing_plan_deleted", plan_id=plan_id)
    return {"deleted": True}


@router.post("/plans/seed")
async def seed_plans(request: Request):
    db_pool = request.app.state.db_pool
    created = 0

    async with db_pool.acquire() as conn:
        for name, config in DEFAULT_PLANS.items():
            exists = await conn.fetchval(
                "SELECT 1 FROM billing_plans WHERE name = $1",
                name,
            )
            if not exists:
                await conn.execute(
                    """
                    INSERT INTO billing_plans (name, price, message_limit, token_limit, features)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    name,
                    config["price"],
                    config["message_limit"],
                    config["token_limit"],
                    None,
                )
                created += 1

    log.info("billing_plans_seeded", count=created)
    return {"seeded": created}


@router.get("/usage/{tenant_id}")
async def get_usage(tenant_id: str, request: Request):
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT period, messages_used, tokens_used, tools_used, storage_mb
            FROM usage_records
            WHERE tenant_id = $1
            ORDER BY period DESC
            LIMIT 12
            """,
            tenant_id,
        )
    return [
        {
            "period": r["period"],
            "messages_used": r["messages_used"],
            "tokens_used": r["tokens_used"],
            "tools_used": r["tools_used"],
            "storage_mb": r["storage_mb"],
        }
        for r in rows
    ]


@router.get("/invoices")
async def list_invoices(
    request: Request,
    tenant_id: str | None = None,
    status: str | None = None,
    period: str | None = None,
):
    db_pool = request.app.state.db_pool
    query = """
        SELECT i.id, i.tenant_id, i.amount, i.status, i.period, i.created_at,
               t.name as tenant_name
        FROM invoices i
        LEFT JOIN tenants t ON i.tenant_id = t.id
        WHERE 1=1
    """
    params = []
    param_idx = 1

    if tenant_id:
        query += f" AND i.tenant_id = ${param_idx}"
        params.append(tenant_id)
        param_idx += 1
    if status:
        query += f" AND i.status = ${param_idx}"
        params.append(status)
        param_idx += 1
    if period:
        query += f" AND i.period = ${param_idx}"
        params.append(period)
        param_idx += 1

    query += " ORDER BY i.created_at DESC LIMIT 100"

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [
        {
            "id": str(r["id"]),
            "tenant_id": str(r["tenant_id"]),
            "tenant_name": r["tenant_name"],
            "amount": r["amount"],
            "status": r["status"],
            "period": r["period"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@router.post("/invoices")
async def create_invoice(body: InvoiceCreate, request: Request):
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO invoices (tenant_id, amount, period, status)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            body.tenant_id,
            body.amount,
            body.period,
            body.status,
        )
    log.info("billing_invoice_created", invoice_id=str(row["id"]), tenant_id=body.tenant_id)
    return {"id": str(row["id"]), "created": True}