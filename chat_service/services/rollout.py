"""Progressive rollout strategy service."""

from __future__ import annotations

import random
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = structlog.get_logger(__name__)


class RolloutStage(Enum):
    SHADOW = "shadow"
    READ_ONLY = "read_only"
    CANARY = "canary"
    GRADUAL = "gradual"
    FULL = "full"


@dataclass
class RollbackTriggers:
    error_rate_threshold: float = 0.05
    latency_threshold_ms: float = 2000.0
    feedback_threshold: float = 3.0


@dataclass
class RolloutMetrics:
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    feedback_score: float = 5.0
    request_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class RolloutStrategy:
    STAGE_ORDER = [RolloutStage.SHADOW, RolloutStage.READ_ONLY, RolloutStage.CANARY, RolloutStage.GRADUAL, RolloutStage.FULL]
    ROLLOUT_PERCENTAGES = {RolloutStage.SHADOW: 0, RolloutStage.READ_ONLY: 0, RolloutStage.CANARY: 5, RolloutStage.GRADUAL: 10, RolloutStage.FULL: 100}

    def __init__(self):
        self.current_stage: RolloutStage = RolloutStage.SHADOW
        self.triggers = RollbackTriggers()
        self._shadow_logs: list[dict] = []

    async def run_shadow(self, agent_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        result = {
            "agent_id": agent_id,
            "stage": self.current_stage.value,
            "input": input_data,
            "timestamp": datetime.utcnow().isoformat(),
            "executed": False,
        }
        self._shadow_logs.append(result)
        return result

    async def canary_split(self, traffic_pct: float) -> list[str]:
        canary_pct = self.ROLLOUT_PERCENTAGES[RolloutStage.CANARY]
        user_ids = [f"user_{i}" for i in range(1000)]
        canary_count = int(1000 * (canary_pct / 100))
        return random.sample(user_ids, canary_count)

    async def gradual_rollout(self, current: RolloutStage, target: RolloutStage) -> RolloutStage:
        if current not in self.STAGE_ORDER or target not in self.STAGE_ORDER:
            return current
        if self.STAGE_ORDER.index(target) <= self.STAGE_ORDER.index(current):
            return current
        idx = self.STAGE_ORDER.index(current) + 1
        next_stage = self.STAGE_ORDER[idx]
        logger.info("rollout_advancing", from_stage=current.value, to_stage=next_stage.value)
        self.current_stage = next_stage
        return next_stage

    async def rollback_if_degraded(self, metrics: RolloutMetrics) -> bool:
        if metrics.error_rate > self.triggers.error_rate_threshold:
            logger.warning("rollback_triggered", reason="error_rate", value=metrics.error_rate)
            return True
        if metrics.avg_latency_ms > self.triggers.latency_threshold_ms:
            logger.warning("rollback_triggered", reason="latency", value=metrics.avg_latency_ms)
            return True
        if metrics.feedback_score < self.triggers.feedback_threshold:
            logger.warning("rollback_triggered", reason="feedback", value=metrics.feedback_score)
            return True
        return False

    def get_shadow_logs(self) -> list[dict]:
        return self._shadow_logs[-100:]