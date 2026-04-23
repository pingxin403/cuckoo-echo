"""Unit tests for progressive rollout."""
import pytest
from chat_service.services.rollout import RolloutStrategy, RolloutStage, RolloutMetrics


class TestRolloutStrategy:
    def test_init(self):
        strategy = RolloutStrategy()
        assert strategy.current_stage == RolloutStage.SHADOW

    @pytest.mark.asyncio
    async def test_run_shadow(self):
        strategy = RolloutStrategy()
        result = await strategy.run_shadow("agent_1", {"query": "test"})
        assert result["agent_id"] == "agent_1"
        assert result["executed"] is False

    @pytest.mark.asyncio
    async def test_canary_split(self):
        strategy = RolloutStrategy()
        canary_users = await strategy.canary_split(5.0)
        assert len(canary_users) == 50

    @pytest.mark.asyncio
    async def test_gradual_rollout(self):
        strategy = RolloutStrategy()
        next_stage = await strategy.gradual_rollout(RolloutStage.SHADOW, RolloutStage.CANARY)
        assert next_stage == RolloutStage.CANARY

    @pytest.mark.asyncio
    async def test_rollback_not_degraded(self):
        strategy = RolloutStrategy()
        metrics = RolloutMetrics(error_rate=0.01, avg_latency_ms=500.0, feedback_score=4.5)
        should_rollback = await strategy.rollback_if_degraded(metrics)
        assert should_rollback is False

    @pytest.mark.asyncio
    async def test_rollback_degraded_error_rate(self):
        strategy = RolloutStrategy()
        metrics = RolloutMetrics(error_rate=0.1, avg_latency_ms=500.0, feedback_score=4.5)
        should_rollback = await strategy.rollback_if_degraded(metrics)
        assert should_rollback is True