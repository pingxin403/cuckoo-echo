"""PII detection and redaction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NamedTuple


class PIIMatch(NamedTuple):
    pii_type: str
    value: str
    start: int
    end: int


class PIIDetector:
    PATTERNS = {
        "email": re.compile(r"[\w.+-]+@[\w-]+\.\w+"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
        "ip": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        "passport": re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
    }

    def detect(self, text: str) -> list[PIIMatch]:
        matches = []
        for pii_type, pattern in self.PATTERNS.items():
            for m in pattern.finditer(text):
                matches.append(PIIMatch(pii_type, m.group(), m.start(), m.end()))
        return matches

    def redact(self, text: str) -> str:
        for pii_type, pattern in self.PATTERNS.items():
            text = pattern.sub(f"[{pii_type.upper()}_REDACTED]", text)
        return text