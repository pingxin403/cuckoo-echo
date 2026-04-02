"""Router node — rule engine + sentiment detection + LLM fallback.

Routing priority:
1. Rule engine (regex patterns) for high-frequency tool intents
2. Negative sentiment / unresolved turns → HITL
3. LLM classification fallback for ambiguous intents
"""
from __future__ import annotations

import re

import structlog

from ai_gateway.client import stream_chat_completion
from chat_service.agent.state import AgentState

log = structlog.get_logger()

# Task 7.1: Compiled regex patterns for deterministic tool routing
RULE_PATTERNS: dict[str, list[re.Pattern]] = {
    "get_order_status": [
        re.compile(r"查.{0,5}订单", re.IGNORECASE),
        re.compile(r"订单.{0,5}状态", re.IGNORECASE),
        re.compile(r"我的订单", re.IGNORECASE),
        re.compile(r"order\s*status", re.IGNORECASE),
        re.compile(r"track.{0,5}order", re.IGNORECASE),
        re.compile(r"where.{0,5}(is|my)\s*order", re.IGNORECASE),
    ],
    "update_shipping_address": [
        re.compile(r"改.{0,5}地址", re.IGNORECASE),
        re.compile(r"修改.{0,5}收货", re.IGNORECASE),
        re.compile(r"更换.{0,5}地址", re.IGNORECASE),
        re.compile(r"change.*address", re.IGNORECASE),
        re.compile(r"update.*address", re.IGNORECASE),
        re.compile(r"modify.*shipping", re.IGNORECASE),
    ],
}

# Task 7.2: Negative sentiment keywords (Chinese + English)
NEGATIVE_KEYWORDS = [
    "投诉", "差评", "垃圾", "骗子", "退款", "太慢", "不满", "生气", "愤怒",
    "恶心", "失望", "无语", "坑", "烂", "废物", "举报",
    "complaint", "terrible", "awful", "angry", "furious", "disgusting",
    "scam", "fraud", "worst", "horrible", "unacceptable",
]
NEGATIVE_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in NEGATIVE_KEYWORDS), re.IGNORECASE
)
UNRESOLVED_THRESHOLD = 3


def detect_negative_sentiment(state: AgentState) -> bool:
    """Detect negative sentiment via keyword matching or unresolved turn count."""
    if state.get("unresolved_turns", 0) >= UNRESOLVED_THRESHOLD:
        return True
    messages = state.get("messages", [])
    if not messages:
        return False
    last_content = messages[-1].get("content", "")
    return bool(NEGATIVE_PATTERN.search(last_content))


# Task 7.3: LLM intent classification fallback
CLASSIFY_PROMPT = """You are an intent classifier for a customer service system.
Classify the user message into exactly one of these categories:
- tool:get_order_status (user wants to check order status)
- tool:update_shipping_address (user wants to change shipping address)
- rag (user is asking a knowledge/FAQ question)
- hitl (user explicitly requests human agent)
- chitchat (casual conversation, greetings)

User message: {text}

Respond with ONLY the category label, nothing else."""


async def llm_classify_intent(text: str, tenant_id: str) -> str:
    """Classify intent via LLM when rule engine misses."""
    try:
        messages = [{"role": "user", "content": CLASSIFY_PROMPT.format(text=text)}]
        response = await stream_chat_completion(
            messages=messages,
            tenant_llm_config={"temperature": 0.0},
        )
        # Collect full response (non-streaming for classification)
        result = ""
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                result += delta.content

        result = result.strip().lower()
        valid = {
            "tool:get_order_status",
            "tool:update_shipping_address",
            "rag",
            "hitl",
            "chitchat",
        }
        if result in valid:
            return result
        log.warning("llm_classify_unrecognized", result=result)
        return "rag"
    except Exception as e:
        log.error("llm_classify_failed", error=str(e))
        return "rag"


# Task 7.4: Router node
async def router_node(state: AgentState) -> AgentState:
    """Route user message: rule engine → sentiment → LLM fallback."""
    messages = state.get("messages", [])
    if not messages:
        return {**state, "user_intent": "rag"}

    text = messages[-1].get("content", "")
    tenant_id = state.get("tenant_id", "")

    # 1. Rule engine (deterministic, ≥99.9% accuracy for matched patterns)
    for tool_name, patterns in RULE_PATTERNS.items():
        if any(p.search(text) for p in patterns):
            log.info("router_rule_hit", tool=tool_name)
            return {**state, "user_intent": f"tool:{tool_name}"}

    # 2. Sentiment / HITL check
    if detect_negative_sentiment(state):
        log.info("router_hitl_triggered", reason="negative_sentiment")
        return {**state, "user_intent": "hitl", "hitl_requested": True}

    # 3. LLM fallback
    intent = await llm_classify_intent(text, tenant_id)
    log.info("router_llm_classified", intent=intent)

    if intent == "hitl":
        return {**state, "user_intent": "hitl", "hitl_requested": True}
    return {**state, "user_intent": intent}


# Task 7.5: Conditional edge function
def route_decision(state: AgentState) -> str:
    """Return routing target based on user_intent."""
    intent = state.get("user_intent", "rag")
    if intent and intent.startswith("tool:"):
        return "tool"
    if state.get("hitl_requested") or intent == "hitl":
        return "hitl"
    return "rag"
