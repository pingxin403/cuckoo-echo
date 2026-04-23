"""Unit tests for evaluation suite."""
import pytest
from chat_service.services.evaluation import EvaluationSuite, TestCase, AgentMetrics


class TestEvaluationSuite:
    def test_init(self):
        suite = EvaluationSuite()
        assert suite.baseline is None
        assert len(suite.eval_history) == 0

    @pytest.mark.asyncio
    async def test_run_trajectory_test(self):
        suite = EvaluationSuite()
        test_case = TestCase(
            task_id="test_1",
            input_query="What is the status?",
            expected_outcome="Return status info",
        )
        result = await suite.run_trajectory_test(test_case)
        assert result.task_id == "test_1"
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_compute_quality_score(self):
        suite = EvaluationSuite()
        result = await suite.run_trajectory_test(
            TestCase("t1", "query", "expected")
        )
        score = await suite.compute_quality_score(result)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_detect_regression_no_change(self):
        suite = EvaluationSuite()
        baseline = AgentMetrics(step_success=1.0, tool_accuracy=1.0)
        current = AgentMetrics(step_success=1.0, tool_accuracy=1.0)
        has_regression = await suite.detect_regression(baseline, current)
        assert has_regression is False

    @pytest.mark.asyncio
    async def test_detect_regression_with_drop(self):
        suite = EvaluationSuite()
        baseline = AgentMetrics(step_success=1.0, tool_accuracy=1.0)
        current = AgentMetrics(step_success=0.8, tool_accuracy=1.0)
        has_regression = await suite.detect_regression(baseline, current)
        assert has_regression is True