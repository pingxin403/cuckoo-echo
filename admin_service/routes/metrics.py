"""Admin Metrics API routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, Query

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1/metrics")

RANGE_MAP = {"1d": "1 day", "7d": "7 days", "30d": "30 days"}


async def _get_ro_pool(request: Request):
    """Get read-only pool (falls back to main pool if RO not configured)."""
    return getattr(request.app.state, "db_pool_ro", request.app.state.db_pool)


@router.get("/overview")
async def metrics_overview(request: Request, range: str = Query("7d")):
    interval = RANGE_MAP.get(range, "7 days")
    tenant_id = request.state.tenant_id
    pool = await _get_ro_pool(request)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""SELECT
                    COUNT(DISTINCT t.id) AS total_conversations,
                    COUNT(DISTINCT h.id) AS hitl_count
                FROM threads t
                LEFT JOIN hitl_sessions h
                    ON h.tenant_id = t.tenant_id
                    AND h.started_at >= NOW() - INTERVAL '{interval}'
                WHERE t.tenant_id = $1
                    AND t.created_at >= NOW() - INTERVAL '{interval}'""",
            tenant_id,
        )
    total = row["total_conversations"] if row else 0
    hitl_count = row["hitl_count"] if row else 0
    return {
        "total_conversations": total,
        "human_transfer_count": hitl_count,
        "human_transfer_rate": round(hitl_count / max(total, 1), 4),
        "range": range,
    }


@router.get("/tokens")
async def metrics_tokens(request: Request, range: str = Query("7d")):
    interval = RANGE_MAP.get(range, "7 days")
    tenant_id = request.state.tenant_id
    pool = await _get_ro_pool(request)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""SELECT COALESCE(SUM(tokens_used), 0) as total_tokens,
                       COUNT(*) as message_count
                FROM messages WHERE tenant_id = $1 AND role = 'assistant'
                AND created_at >= NOW() - INTERVAL '{interval}'""",
            tenant_id,
        )
    return {
        "total_tokens": row["total_tokens"] if row else 0,
        "message_count": row["message_count"] if row else 0,
        "range": range,
    }


@router.get("/missed-queries")
async def metrics_missed_queries(request: Request, range: str = Query("7d")):
    interval = RANGE_MAP.get(range, "7 days")
    tenant_id = request.state.tenant_id
    pool = await _get_ro_pool(request)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""SELECT LEFT(content, 50) as query_prefix, COUNT(*) as count
                FROM messages
                WHERE tenant_id = $1 AND role = 'user'
                AND created_at >= NOW() - INTERVAL '{interval}'
                AND (
                    thread_id IN (SELECT thread_id FROM hitl_sessions WHERE tenant_id = $1)
                )
                GROUP BY query_prefix
                ORDER BY count DESC
                LIMIT 20""",
            tenant_id,
        )
    return {"missed_queries": [dict(r) for r in rows], "range": range}


@router.post("/sandbox/run")
async def sandbox_run(request: Request):
    """Run RAG quality gate with Ragas metrics."""
    body = await request.json()
    # tenant_id: kept for potential future use in sandbox evaluation
    test_cases = body.get("test_cases", [])

    if not test_cases:
        return {"status": "error", "message": "No test cases provided"}

    try:
        from ragas import evaluate, EvaluationDataset
        from ragas.metrics import Faithfulness, ContextPrecision, ContextRecall, AnswerRelevancy

        # Build evaluation dataset from test cases
        dataset = []
        for case in test_cases:
            dataset.append(
                {
                    "user_input": case.get("query", ""),
                    "retrieved_contexts": case.get("contexts", []),
                    "response": case.get("response", ""),
                    "reference": case.get("reference", ""),
                }
            )

        eval_dataset = EvaluationDataset.from_list(dataset)
        result = evaluate(
            dataset=eval_dataset,
            metrics=[Faithfulness(), ContextPrecision(), ContextRecall(), AnswerRelevancy()],
        )

        # Quality gate thresholds
        thresholds = {
            "faithfulness": 0.85,
            "context_precision": 0.80,
            "context_recall": 0.75,
            "answer_relevancy": 0.85,
        }

        scores = {k: float(v) for k, v in result.items() if isinstance(v, (int, float))}
        failed = {k: v for k, v in scores.items() if v < thresholds.get(k, 0)}

        return {
            "status": "passed" if not failed else "failed",
            "scores": scores,
            "thresholds": thresholds,
            "failed_metrics": failed,
            "test_cases_count": len(test_cases),
        }
    except ImportError:
        return {"status": "stub", "message": "Ragas not installed", "test_cases_count": len(test_cases)}
    except Exception as e:
        log.error("sandbox_run_failed", error=str(e))
        return {"status": "error", "message": str(e), "test_cases_count": len(test_cases)}
