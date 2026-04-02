"""Guardrails node — NLI hallucination detection + postprocess.

Uses CrossEncoder NLI model to verify LLM responses are entailed by RAG context.
When hallucination detected: pushes correction message + triggers HITL.
"""
from __future__ import annotations

import asyncio

import structlog

from chat_service.agent.state import AgentState

log = structlog.get_logger()

# Task 9.1: NLI model singleton (lazy-loaded to avoid import-time model download)
# Label order: contradiction=0, entailment=1, neutral=2
_nli_model = None


def _get_nli_model():
    """Lazy-load the NLI CrossEncoder model."""
    global _nli_model
    if _nli_model is None:
        try:
            from sentence_transformers import CrossEncoder

            _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-small")
            log.info("nli_model_loaded", model="cross-encoder/nli-deberta-v3-small")
        except Exception as e:
            log.error("nli_model_load_failed", error=str(e))
    return _nli_model


CORRECTION_MESSAGE = "⚠️ 抱歉，刚才的回答可能有误，已为您转接人工客服核实。"
ENTAILMENT_THRESHOLD = 0.5
NLI_TIMEOUT = 0.3


# Task 9.2-9.3: Guardrails node
async def guardrails_node(state: AgentState) -> AgentState:
    """NLI hallucination detection on RAG responses.

    Skips if rag_context is empty (non-RAG path like tool calls or chitchat).
    On hallucination: sets correction_message + hitl_requested.
    On timeout: passes through (degrades gracefully).
    """
    response = state.get("llm_response", "")
    rag_context = state.get("rag_context", [])

    # Non-RAG path: skip NLI
    if not rag_context:
        return {**state, "guardrails_passed": True}

    if not response:
        return {**state, "guardrails_passed": True}

    nli_model = _get_nli_model()
    if nli_model is None:
        log.warning("nli_model_not_available", msg="skipping guardrails")
        return {**state, "guardrails_passed": True}

    try:
        pairs = [(ctx, response) for ctx in rag_context]
        loop = asyncio.get_running_loop()
        scores = await asyncio.wait_for(
            loop.run_in_executor(
                None, lambda: nli_model.predict(pairs, apply_softmax=True)
            ),
            timeout=NLI_TIMEOUT,
        )
        # scores shape: (n_pairs, 3) — [contradiction, entailment, neutral]
        max_entailment = max(s[1] for s in scores)

        if max_entailment < ENTAILMENT_THRESHOLD:
            log.warning(
                "hallucination_detected",
                thread_id=state.get("thread_id"),
                max_entailment=float(max_entailment),
            )
            return {
                **state,
                "guardrails_passed": False,
                "correction_message": CORRECTION_MESSAGE,
                "hitl_requested": True,
            }
    except asyncio.TimeoutError:
        log.warning("guardrails_nli_timeout", thread_id=state.get("thread_id"))
    except Exception as e:
        log.error("guardrails_error", error=str(e))

    return {**state, "guardrails_passed": True}


# Task 9.4: Postprocess node
async def postprocess_node(state: AgentState) -> AgentState:
    """Post-processing: handle correction messages and update turn counters."""
    correction = state.get("correction_message")
    if correction:
        log.info("pushing_correction", thread_id=state.get("thread_id"))
        # correction_message will be picked up by event_generator for SSE push

    # Increment unresolved_turns if guardrails failed
    unresolved = state.get("unresolved_turns", 0)
    if not state.get("guardrails_passed", True):
        unresolved += 1

    return {**state, "unresolved_turns": unresolved}


# Task 9.5: Conditional edge function
def guardrails_decision(state: AgentState) -> str:
    """Return 'hitl' if HITL requested, 'pass' otherwise."""
    return "hitl" if state.get("hitl_requested") else "pass"
