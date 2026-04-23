"""Agent safety guardrails with defense-in-depth."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger()


class SafetyLevel(Enum):
    SAFE = "safe"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class SafetyResult:
    level: SafetyLevel
    reason: str
    violations: list[str] = field(default_factory=list)
    sanitized_content: str | None = None


@dataclass
class PIIPattern:
    pattern: re.Pattern
    label: str
    replacement: str = "[REDACTED]"


class PIIDetector:
    """Detects and redact Personally Identifiable Information."""

    PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email", "[EMAIL]"),
        (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone", "[PHONE]"),
        (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "credit_card", "[CARD]"),
        (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "ssn", "[SSN]"),
        (r"\b[A-Z]\d[A-Z][-\s]?\d[A-Z]\d\b", "passport", "[PASSPORT]"),
        (r"\b(?:street|avenue|road|blvd)[.,?\s]+\w+", "address", "[ADDRESS]"),
    ]

    def __init__(self):
        self._compiled: list[PIIPattern] = [
            PIIPattern(re.compile(p, re.I), label, rep)
            for p, label, rep in self.PATTERNS
        ]

    def detect(self, text: str) -> list[tuple[str, str]]:
        findings = []
        for pii in self._compiled:
            matches = pii.pattern.finditer(text)
            findings.extend((m.group(), pii.label) for m in matches)
        return findings

    def redact(self, text: str) -> tuple[str, list[str]]:
        redacted = text
        all_found: list[str] = []

        for pii in self._compiled:
            matches = pii.pattern.findall(text)
            all_found.extend(matches)
            redacted = pii.pattern.sub(pii.replacement, redacted)

        return redacted, all_found


class OutputFilter:
    """Filters potentially harmful content from LLM output."""

    BLOCK_PATTERNS = [
        r"(hack|exploit|vulnerability)\s+(system|server|database|account)",
        r"(steal|bypass|steal|phish)\s+(credentials|passwords|data)",
        r"(generate|create)\s+(malware|virus|ransomware|trojan)",
    ]

    WARN_PATTERNS = [
        r"(confidential|proprietary|secret)\s+(information|data|document)",
        r"(internal|private|restricted)\s+(code|document|policy)",
    ]

    def __init__(self):
        self._block = [re.compile(p, re.I) for p in self.BLOCK_PATTERNS]
        self._warn = [re.compile(p, re.I) for p in self.WARN_PATTERNS]

    def check(self, text: str) -> SafetyResult:
        violations: list[str] = []

        for pattern in self._block:
            match = pattern.search(text)
            if match:
                violations.append(f"blocked_pattern: {match.group()}")

        for pattern in self._warn:
            match = pattern.search(text)
            if match:
                violations.append(f"warning_pattern: {match.group()}")

        if violations:
            blocked = any("blocked" in v for v in violations)
            level = SafetyLevel.BLOCK if blocked else SafetyLevel.WARN
            return SafetyResult(level=level, reason="Policy violation", violations=violations)

        return SafetyResult(level=SafetyLevel.SAFE, reason="Content passed all checks")

    def sanitize(self, text: str) -> str:
        for pattern in self._block:
            text = pattern.sub("[FILTERED: potentially harmful content]", text)
        return text


class AgentSafetyGuardrails:
    """Defense-in-depth safety system for agent actions."""

    def __init__(self):
        self._pii_detector = PIIDetector()
        self._output_filter = OutputFilter()
        self._allowed_tools: set[str] = set()
        self._blocked_domains: set[str] = set()

    def set_allowed_tools(self, tools: list[str]) -> None:
        self._allowed_tools = set(tools)
        logger.info("allowed_tools_updated", count=len(self._allowed_tools))

    def set_blocked_domains(self, domains: list[str]) -> None:
        self._blocked_domains = set(domains)
        logger.info("blocked_domains_updated", count=len(self._blocked_domains))

    def check_tool_permission(self, tool_name: str) -> SafetyResult:
        if not self._allowed_tools:
            return SafetyResult(level=SafetyLevel.SAFE, reason="No allowlist active")

        if tool_name not in self._allowed_tools:
            return SafetyResult(
                level=SafetyLevel.BLOCK,
                reason=f"Tool '{tool_name}' not in allowed list",
                violations=[f"disallowed_tool: {tool_name}"],
            )
        return SafetyResult(level=SafetyLevel.SAFE, reason=f"Tool '{tool_name}' permitted")

    def check_domain_permission(self, url: str) -> SafetyResult:
        if not self._blocked_domains:
            return SafetyResult(level=SafetyLevel.SAFE, reason="No domain blocking active")

        for domain in self._blocked_domains:
            if domain in url:
                return SafetyResult(
                    level=SafetyLevel.BLOCK,
                    reason=f"Domain '{domain}' is blocked",
                    violations=[f"blocked_domain: {domain}"],
                )
        return SafetyResult(level=SafetyLevel.SAFE, reason="Domain permitted")

    def inspect_input(self, text: str) -> SafetyResult:
        findings = self._pii_detector.detect(text)

        if not findings:
            return SafetyResult(level=SafetyLevel.SAFE, reason="No PII detected")

        return SafetyResult(
            level=SafetyLevel.WARN,
            reason=f"Detected {len(findings)} potential PII items",
            violations=[f"pii: {label}" for _, label in findings],
        )

    def inspect_output(self, text: str) -> SafetyResult:
        filter_result = self._output_filter.check(text)

        if filter_result.level != SafetyLevel.SAFE:
            return filter_result

        findings = self._pii_detector.detect(text)

        if findings:
            return SafetyResult(
                level=SafetyLevel.WARN,
                reason=f"Detected {len(findings)} potential PII in output",
                violations=[f"pii: {label}" for _, label in findings],
                sanitized_content=self._pii_detector.redact(text)[0],
            )

        return SafetyResult(level=SafetyLevel.SAFE, reason="Output passed all checks")

    def sanitize_content(self, text: str) -> str:
        text = self._output_filter.sanitize(text)
        redacted, _ = self._pii_detector.redact(text)
        return redacted


guardrails = AgentSafetyGuardrails()