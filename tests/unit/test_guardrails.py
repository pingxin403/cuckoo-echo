"""Unit tests for Guardrails node."""
import pytest
from unittest.mock import MagicMock, patch

import numpy as np

from chat_service.agent.nodes.guardrails import (
    CORRECTION_MESSAGE,
    guardrails_decision,
    guardrails_node,
    postprocess_node,
)
from chat_service.agent.state import AgentState


class TestGuardrailsNode:
    @pytest.mark.asyncio
    async def test_skips_when_no_rag_context(self):
        state = AgentState(rag_context=[], llm_response="hello")
        result = await guardrails_node(state)
        assert result["guardrails_passed"] is True

    @pytest.mark.asyncio
    async def test_skips_when_no_response(self):
        state = AgentState(rag_context=["some context"], llm_response="")
        result = await guardrails_node(state)
        assert result["guardrails_passed"] is True

    @pytest.mark.asyncio
    async def test_entailment_above_threshold_passes(self):
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([[0.1, 0.8, 0.1]])

        state = AgentState(
            rag_context=["The return policy is 7 days"],
            llm_response="You can return within 7 days",
            thread_id="t1",
        )
        with patch(
            "chat_service.agent.nodes.guardrails._get_nli_model",
            return_value=mock_model,
        ):
            result = await guardrails_node(state)
        assert result["guardrails_passed"] is True
        assert result.get("hitl_requested") is not True

    @pytest.mark.asyncio
    async def test_entailment_below_threshold_triggers_correction(self):
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([[0.7, 0.1, 0.2]])

        state = AgentState(
            rag_context=["The return policy is 7 days"],
            llm_response="You can return within 30 days",
            thread_id="t1",
        )
        with patch(
            "chat_service.agent.nodes.guardrails._get_nli_model",
            return_value=mock_model,
        ):
            result = await guardrails_node(state)
        assert result["guardrails_passed"] is False
        assert result["correction_message"] == CORRECTION_MESSAGE
        assert result["hitl_requested"] is True

    @pytest.mark.asyncio
    async def test_timeout_degrades_gracefully(self):
        mock_model = MagicMock()

        def slow_predict(*args, **kwargs):
            import time

            time.sleep(10)
            return np.array([[0.1, 0.8, 0.1]])

        mock_model.predict.side_effect = slow_predict

        state = AgentState(
            rag_context=["context"],
            llm_response="response",
        )
        with patch(
            "chat_service.agent.nodes.guardrails._get_nli_model",
            return_value=mock_model,
        ):
            with patch("chat_service.agent.nodes.guardrails.NLI_TIMEOUT", 0.01):
                result = await guardrails_node(state)
        assert result["guardrails_passed"] is True

    @pytest.mark.asyncio
    async def test_model_not_available_passes_through(self):
        state = AgentState(rag_context=["ctx"], llm_response="resp")
        with patch(
            "chat_service.agent.nodes.guardrails._get_nli_model",
            return_value=None,
        ):
            result = await guardrails_node(state)
        assert result["guardrails_passed"] is True


class TestPostprocessNode:
    @pytest.mark.asyncio
    async def test_increments_unresolved_on_failed_guardrails(self):
        state = AgentState(guardrails_passed=False, unresolved_turns=2)
        result = await postprocess_node(state)
        assert result["unresolved_turns"] == 3

    @pytest.mark.asyncio
    async def test_no_increment_on_passed_guardrails(self):
        state = AgentState(guardrails_passed=True, unresolved_turns=2)
        result = await postprocess_node(state)
        assert result["unresolved_turns"] == 2

    @pytest.mark.asyncio
    async def test_correction_message_preserved(self):
        state = AgentState(correction_message="⚠️ test", guardrails_passed=False)
        result = await postprocess_node(state)
        assert result["correction_message"] == "⚠️ test"


class TestGuardrailsDecision:
    def test_pass(self):
        assert guardrails_decision(AgentState(hitl_requested=False)) == "pass"

    def test_hitl(self):
        assert guardrails_decision(AgentState(hitl_requested=True)) == "hitl"

    def test_default(self):
        assert guardrails_decision(AgentState()) == "pass"
