"""Intent recognition and entity extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IntentLevel(Enum):
    DOMAIN = "domain"
    TASK = "task"
    SUBTASK = "subtask"
    PARAMETER = "parameter"


class EntityType(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    DATETIME = "datetime"
    NUMBER = "number"
    LOCATION = "location"
    PRODUCT = "product"
    STATUS = "status"


@dataclass
class Entity:
    type: EntityType
    value: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "value": self.value,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
        }


INTENT_PATTERNS = {
    "greeting": [
        r"^(你好|您好|hello|hi|hey|嗨)",
        r"^(早上好|下午好|晚上好)",
    ],
    "query": [
        r"^(什么|怎么|如何|为什么|哪里|谁|多少|几)",
        r"^(what|how|why|where|who|when)",
    ],
    "task": {
        "search": [r"(找|搜索|查找|look for|search|find)"],
        "create": [r"(创建|新增|添加|add|create|new)"],
        "update": [r"(修改|更新|编辑|edit|update|change)"],
        "delete": [r"(删除|移除|取消|delete|remove|cancel)"],
    },
    "help": [
        r"(帮助|help|support|assist|帮帮我)",
    ],
    "complaint": [
        r"(问题|issue|problem|投诉|差评|complaint)",
    ],
}


def classify_intent(text: str) -> tuple[str, float]:
    """Classify intent using rule-based matching."""
    text_lower = text.lower().strip()

    for greeting in INTENT_PATTERNS.get("greeting", []):
        if re.search(greeting, text_lower):
            return "greeting", 0.95

    for query in INTENT_PATTERNS.get("query", []):
        if re.search(query, text_lower):
            return "query", 0.9

    for help_pat in INTENT_PATTERNS.get("help", []):
        if re.search(help_pat, text_lower):
            return "help", 0.9

    for complaint in INTENT_PATTERNS.get("complaint", []):
        if re.search(complaint, text_lower):
            return "complaint", 0.85

    for task_type, patterns in INTENT_PATTERNS.get("task", {}).items():
        for pat in patterns:
            if re.search(pat, text_lower):
                return f"task:{task_type}", 0.85

    return "query", 0.5


def extract_entities(text: str) -> list[Entity]:
    """Extract entities using simple pattern matching."""
    entities = []

    datetime_patterns = [
        (r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)", EntityType.DATETIME),
        (r"(今天|明天|昨天|上周|下周|下周)", EntityType.DATETIME),
    ]

    number_patterns = [
        (r"(\d+\s*(个|件|次|条|元|块))", EntityType.NUMBER),
        (r"(\d+)", EntityType.NUMBER),
    ]

    for pattern, entity_type in datetime_patterns + number_patterns:
        for match in re.finditer(pattern, text):
            entities.append(Entity(
                type=entity_type,
                value=match.group(1),
                start=match.start(),
                end=match.end(),
                confidence=0.8,
            ))

    return entities


def compute_confidence(
    intent: str,
    entities: list[Entity],
    context: dict,
) -> float:
    """Compute overall classification confidence."""
    intent_score = 0.6 if intent.startswith("task:") else 0.8

    entity_coverage = min(1.0, len(entities) / 2)

    context_score = context.get("historical_accuracy", 0.5)

    weights = {
        "intent": 0.5,
        "entities": 0.3,
        "context": 0.2,
    }

    return (
        intent_score * weights["intent"]
        + entity_coverage * weights["entities"]
        + context_score * weights["context"]
    )


def detect_multi_intent(text: str) -> list[str]:
    """Detect multiple intents in a single message."""
    conjunctions = ["和", "并且", "and", "also"]
    intents = []

    for conj in conjunctions:
        if conj in text:
            parts = text.split(conj)
            for part in parts:
                intent, _ = classify_intent(part.strip())
                intents.append(intent)
            return intents

    intent, _ = classify_intent(text)
    return [intent]
