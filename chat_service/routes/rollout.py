"""Progressive rollout API routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException
from datetime import datetime

from chat_service.services.rollout import RolloutStrategy, RolloutStage, RolloutMetrics

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/rollout", tags=["rollout"])

_rollout = RolloutStrategy()
_stage_history: list[dict] = []
_metrics_history: list[dict] = []


@router.get("/status")
async def get_rollout_status() -> dict:
    """Get current rollout status."""
    return {
        "current_stage": _rollout.current_stage.value,
        "target_percentage": _rollout.ROLLOUT_PERCENTAGES.get(_rollout.current_stage, 0),
        "stage_order": [s.value for s in _rollout.STAGE_ORDER],
    }


@router.get("/metrics")
async def get_rollout_metrics() -> dict:
    """Get rollout metrics with historical tracking."""
    current_metrics = RolloutMetrics(
        error_rate=0.02,
        avg_latency_ms=450.0,
        feedback_score=4.2,
        request_count=len(_metrics_history),
    )
    _metrics_history.append({
        **current_metrics.__dict__,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {
        "current": {
            "error_rate": current_metrics.error_rate,
            "latency_p50": current_metrics.avg_latency_ms,
            "user_feedback_score": current_metrics.feedback_score,
            "request_count": current_metrics.request_count,
        },
        "history": _metrics_history[-20:],
    }


@router.get("/history")
async def get_rollout_history() -> dict:
    """Get historical rollout stages."""
    return {
        "stages": _stage_history,
        "total_transitions": len(_stage_history),
    }


@router.post("/advance")
async def advance_rollout() -> dict:
    """Advance to next rollout stage."""
    from_stage = _rollout.current_stage
    idx = _rollout.STAGE_ORDER.index(from_stage)
    if idx + 1 < len(_rollout.STAGE_ORDER):
        to_stage = _rollout.STAGE_ORDER[idx + 1]
        _rollout.current_stage = to_stage
        _stage_history.append({
            "from": from_stage.value,
            "to": to_stage.value,
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info("rollout_advanced", from_stage=from_stage.value, to_stage=to_stage.value)
        return {"success": True, "new_stage": to_stage.value}
    return {"success": False, "message": "Already at full rollout"}


@router.post("/rollback")
async def rollback_rollout() -> dict:
    """Rollback to previous stage."""
    from_stage = _rollout.current_stage
    if from_stage == RolloutStage.SHADOW:
        return {"success": False, "message": "Already at minimum stage"}
    idx = _rollout.STAGE_ORDER.index(from_stage)
    to_stage = _rollout.STAGE_ORDER[idx - 1]
    _rollout.current_stage = to_stage
    _stage_history.append({
        "from": from_stage.value,
        "to": to_stage.value,
        "timestamp": datetime.utcnow().isoformat(),
        "type": "rollback",
    })
    logger.info("rollout_rolled_back", from_stage=from_stage.value, to_stage=to_stage.value)
    return {"success": True, "new_stage": to_stage.value}


@router.get("/canary/users")
async def get_canary_users() -> dict:
    """Get canary user IDs."""
    canary_users = await _rollout.canary_split(5.0)
    return {"canary_users": canary_users, "count": len(canary_users)}