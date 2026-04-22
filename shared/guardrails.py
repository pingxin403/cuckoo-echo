"""Agent safety guardrails - Defense in depth."""

from __future__ import annotations

import re
import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = structlog.get_logger(__name__)


class GuardrailAction(Enum):
    BLOCK = "block"
    WARN = "warn"
    LOG = "log"


@dataclass
class GuardrailResult:
    passed: bool
    triggered: str | None = None
    confidence: float = 1.0
    action: GuardrailAction = GuardrailAction.LOG
    details: dict[str, Any] = field(default_factory=dict)


class GuardrailEngine:
    def __init__(self):
        from shared.pii_detector import PIIDetector
        from shared.action_policy import ActionPolicy

        self.pii_detector = PIIDetector()
        self.action_policy = ActionPolicy()
        self._input_patterns = self._load_input_patterns()
        self._output_patterns = self._load_output_patterns()

    def _load_input_patterns(self) -> list[re.Pattern]:
        return [
            re.compile(r"<script.*?>", re.I),
            re.compile(r"javascript:", re.I),
            re.compile(r"on\w+\s*=", re.I),
        ]

    def _load_output_patterns(self) -> list[re.Pattern]:
        return [
            re.compile(r"i'm not sure|^maybe|^perhaps", re.I),
        ]

    async def check_input(self, text: str) -> GuardrailResult:
        if not text:
            return GuardrailResult(passed=True)

        for pattern in self._input_patterns:
            if pattern.search(text):
                return GuardrailResult(
                    passed=False,
                    triggered="prompt_injection",
                    confidence=0.9,
                    action=GuardrailAction.BLOCK,
                    details={"pattern": pattern.pattern},
                )

        pii_matches = self.pii_detector.detect(text)
        if pii_matches:
            return GuardrailResult(
                passed=True,
                triggered="pii_detected",
                confidence=0.95,
                action=GuardrailAction.WARN,
                details={"pii_count": len(pii_matches)},
            )

        return GuardrailResult(passed=True)

    async def check_output(self, text: str) -> GuardrailResult:
        if not text:
            return GuardrailResult(passed=True)

        for pattern in self._output_patterns:
            if pattern.search(text):
                return GuardrailResult(
                    passed=True,
                    triggered="uncertain_output",
                    confidence=0.7,
                    action=GuardrailAction.WARN,
                    details={"pattern": pattern.pattern},
                )

        return GuardrailResult(passed=True)

    async def check_action(self, tool: str, params: dict[str, Any]) -> GuardrailResult:
        return await self.action_policy.check_action(tool, params)