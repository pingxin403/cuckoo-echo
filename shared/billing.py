"""Billing service for token and multimodal credit tracking."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

import structlog
from asyncpg import Pool

from shared.db import tenant_db_context

log = structlog.get_logger()

AUDIO_CREDIT_RATE = 0.1  # credits per 15-second chunk
IMAGE_CREDIT_RATES = {"sd": 0.5, "hd": 1.0, "4k": 2.0}  # by resolution tier

DEFAULT_PLANS = {
    "Free": {"price": 0, "message_limit": 100, "token_limit": 10000},
    "Starter": {"price": 49, "message_limit": 1000, "token_limit": 100000},
    "Pro": {"price": 199, "message_limit": 5000, "token_limit": 500000},
    "Enterprise": {"price": 0, "message_limit": -1, "token_limit": -1},
}


@dataclass
class UsageRecord:
    tenant_id: str
    period: str
    messages_used: int = 0
    tokens_used: int = 0
    tools_used: int = 0
    storage_mb: int = 0


@dataclass
class BillingAccount:
    tenant_id: str
    plan_id: Optional[str]
    balance: Decimal
    credit_limit: Decimal
    status: str


def calculate_audio_credits(audio_seconds: float) -> float:
    """Calculate audio credits: ceil(seconds/15) * rate."""
    if audio_seconds <= 0:
        return 0.0
    chunks = math.ceil(audio_seconds / 15)
    return chunks * AUDIO_CREDIT_RATE


def calculate_image_credits(resolution_tier: str = "sd") -> float:
    """Calculate image credits by resolution tier."""
    return IMAGE_CREDIT_RATES.get(resolution_tier, IMAGE_CREDIT_RATES["sd"])


async def record_usage(
    thread_id: str,
    tenant_id: str,
    tokens_used: int,
    db_pool=None,
    audio_seconds: float = 0.0,
    image_count: int = 0,
    image_resolution: str = "sd",
) -> None:
    """Record token usage and multimodal credits for billing.

    Updates the latest assistant message in the thread with token count.
    Also records multimodal credits if applicable.
    """
    # Calculate multimodal credits
    audio_credits = calculate_audio_credits(audio_seconds)
    image_credits = calculate_image_credits(image_resolution) * image_count
    total_credits = audio_credits + image_credits

    if db_pool is None:
        log.warning("billing_no_db_pool", thread_id=thread_id)
        return

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            await conn.execute(
                """
                UPDATE messages SET tokens_used = $1
                WHERE thread_id = $2 AND role = 'assistant'
                AND created_at = (
                    SELECT MAX(created_at) FROM messages
                    WHERE thread_id = $2 AND role = 'assistant'
                )
                """,
                tokens_used,
                thread_id,
            )

    log.info(
        "billing_recorded",
        thread_id=thread_id,
        tokens=tokens_used,
        audio_seconds=audio_seconds,
        audio_credits=audio_credits,
        image_count=image_count,
        image_credits=image_credits,
        total_credits=total_credits,
    )


async def get_or_create_account(
    db_pool: Pool,
    tenant_id: str,
) -> BillingAccount:
    """Get or create billing account for tenant."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, plan_id, balance, credit_limit, status
            FROM billing_accounts WHERE tenant_id = $1
            """,
            tenant_id,
        )
        if row:
            return BillingAccount(
                tenant_id=str(row["tenant_id"]),
                plan_id=str(row["plan_id"]) if row["plan_id"] else None,
                balance=row["balance"],
                credit_limit=row["credit_limit"],
                status=row["status"],
            )

        free_plan = await conn.fetchrow(
            "SELECT id FROM billing_plans WHERE name = 'Free'"
        )
        plan_id = str(free_plan["id"]) if free_plan else None

        await conn.execute(
            """
            INSERT INTO billing_accounts (tenant_id, plan_id, balance, credit_limit, status)
            VALUES ($1, $2, 0, 0, 'active')
            """,
            tenant_id,
            plan_id,
        )
        return BillingAccount(
            tenant_id=tenant_id,
            plan_id=plan_id,
            balance=Decimal("0"),
            credit_limit=Decimal("0"),
            status="active",
        )


async def check_limit(
    db_pool: Pool,
    tenant_id: str,
    resource: str,
    amount: int,
) -> tuple[bool, str]:
    """Check if tenant has available limit for resource.

    Returns (allowed, reason) - allowed is False if limit exceeded.
    """
    account = await get_or_create_account(db_pool, tenant_id)
    if account.status != "active":
        return False, f"Account status: {account.status}"

    period = datetime.now().strftime("%Y-%m")

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            usage = await conn.fetchrow(
                """
                SELECT messages_used, tokens_used, tools_used
                FROM usage_records
                WHERE tenant_id = current_setting('app.current_tenant')::UUID AND period = $1
                """,
                period,
            )

            plan = await conn.fetchrow(
                "SELECT message_limit, token_limit FROM billing_plans WHERE id = $1",
                account.plan_id,
            )

            if not plan:
                return True, "No plan limit"

            current_usage = usage.get(resource + "_used", 0) if usage else 0
            limit = plan.get(resource + "_limit", -1)

            if limit == -1:
                return True, "Unlimited"

            if current_usage + amount > limit:
                return False, f"{resource} limit exceeded: {current_usage}/{limit}"

            return True, "OK"


async def record_usage_to_db(
    db_pool: Pool,
    tenant_id: str,
    messages: int = 0,
    tokens: int = 0,
    tools: int = 0,
    storage_mb: int = 0,
) -> None:
    """Record usage to usage_records table."""
    period = datetime.now().strftime("%Y-%m")

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            await conn.execute(
                """
                INSERT INTO usage_records (tenant_id, period, messages_used, tokens_used, tools_used, storage_mb)
                VALUES (current_setting('app.current_tenant')::UUID, $1, $2, $3, $4, $5)
                ON CONFLICT (tenant_id, period) DO UPDATE SET
                    messages_used = usage_records.messages_used + $2,
                    tokens_used = usage_records.tokens_used + $3,
                    tools_used = usage_records.tools_used + $4,
                    storage_mb = usage_records.storage_mb + $5
                """,
                period,
                messages,
                tokens,
                tools,
                storage_mb,
            )

    log.info(
        "usage_recorded",
        tenant_id=tenant_id,
        period=period,
        messages=messages,
        tokens=tokens,
        tools=tools,
    )
