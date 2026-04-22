"""Tool action policy and allowlisting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shared.guardrails import GuardrailAction, GuardrailEngine, GuardrailResult


class ActionPolicy:
    DEFAULT_ALLOWED_TOOLS = [
        "search_knowledge",
        "get_order_status",
        "calculate_refund",
        "escalate_to_human",
        "transfer",
        "get_customer_info",
    ]

    def __init__(self, allowed_tools: list[str] | None = None):
        self.allowed_tools = allowed_tools or self.DEFAULT_ALLOWED_TOOLS.copy()

    async def check_action(self, tool: str, params: dict[str, Any]) -> GuardrailResult:
        if tool not in self.allowed_tools:
            return GuardrailResult(
                passed=False,
                triggered="tool_not_allowed",
                confidence=1.0,
                action=GuardrailAction.BLOCK,
                details={"tool": tool, "allowed": self.allowed_tools},
            )
        return GuardrailResult(passed=True, action=GuardrailAction.LOG)

    def add_allowed_tool(self, tool: str) -> None:
        if tool not in self.allowed_tools:
            self.allowed_tools.append(tool)

    def remove_allowed_tool(self, tool: str) -> None:
        if tool in self.allowed_tools:
            self.allowed_tools.remove(tool)