"""Chain of Thought reasoning engine."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional


class NodeStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    PRUNED = "pruned"


@dataclass
class ReasoningStep:
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    thought: str = ""
    action: Optional[str] = None
    observation: Optional[str] = None
    confidence: float = 1.0
    parent_id: Optional[str] = None
    children: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation,
            "confidence": self.confidence,
            "parent_id": self.parent_id,
            "children": self.children,
            "timestamp": self.timestamp.isoformat(),
        }


class ReasoningTrace:
    def __init__(self):
        self.steps: list[ReasoningStep] = []
        self.root_id: Optional[str] = None

    def add_step(self, step: ReasoningStep) -> str:
        if not self.root_id:
            self.root_id = step.step_id
        else:
            step.parent_id = self.steps[-1].step_id if self.steps else None
            if step.parent_id:
                parent = self.get_step(step.parent_id)
                if parent:
                    parent.children.append(step.step_id)
        self.steps.append(step)
        return step.step_id

    def get_step(self, step_id: str) -> Optional[ReasoningStep]:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def is_complete(self) -> bool:
        return len(self.steps) > 0 and self.steps[-1].confidence >= 0.9

    def to_dict(self) -> dict:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "root_id": self.root_id,
            "is_complete": self.is_complete(),
        }


class CoTEngine:
    def __init__(self, llm_client: Optional[object] = None):
        self.llm_client = llm_client

    COT_PROMPT = """You are a reasoning assistant. Think step by step.
    
Query: {query}

Provide your reasoning as a series of clear steps. For each step:
1. State your thought
2. Take an action if needed
3. Note the observation/result

End with your final answer.
"""

    async def generate_with_cot(
        self,
        query: str,
        max_steps: int = 10,
        stream_callback: Optional[Callable[[ReasoningStep], None]] = None,
    ) -> ReasoningTrace:
        trace = ReasoningTrace()
        context = ""
        step_count = 0

        while step_count < max_steps:
            prompt = self.COT_PROMPT.format(query=query, context=context)

            step = ReasoningStep(
                thought=f"Step {step_count + 1}: Analyzing query...",
                confidence=0.5,
            )

            if self.llm_client:
                response = await self.llm_client.generate(prompt)
                step.thought = self._parse_thought(response)
                step.observation = self._parse_observation(response)
                step.confidence = self._estimate_confidence(response)

            trace.add_step(step)

            if stream_callback:
                stream_callback(step)

            if trace.is_complete():
                break

            context += f"\nStep {step_count + 1}: {step.thought}"
            if step.observation:
                context += f" → {step.observation}"

            step_count += 1

        return trace

    def _parse_thought(self, response: str) -> str:
        lines = response.strip().split("\n")
        for line in lines:
            if line.strip():
                return line.strip()
        return response[:100]

    def _parse_observation(self, response: str) -> Optional[str]:
        if "→" in response:
            parts = response.split("→")
            if len(parts) > 1:
                return parts[-1].strip()
        return None

    def _estimate_confidence(self, response: str) -> float:
        uncertainty_markers = ["maybe", "perhaps", "possibly", "可能", "也许", "不确定"]
        for marker in uncertainty_markers:
            if marker.lower() in response.lower():
                return 0.6
        return 0.8


class ToTNode:
    def __init__(
        self,
        thought: str,
        parent: Optional["ToTNode"] = None,
        depth: int = 0,
    ):
        self.node_id = str(uuid.uuid4())[:8]
        self.thought = thought
        self.score: float = 0.0
        self.parent = parent
        self.children: list["ToTNode"] = []
        self.depth = depth
        self.status = NodeStatus.PENDING

    def add_child(self, child: "ToTNode"):
        self.children.append(child)
        child.parent = self

    def get_path(self) -> list[str]:
        path = [self.thought]
        current = self.parent
        while current:
            path.insert(0, current.thought)
            current = current.parent
        return path


class ToTEngine:
    def __init__(self, llm_client: Optional[object] = None):
        self.llm_client = llm_client

    async def search(
        self,
        query: str,
        branching: int = 3,
        depth: int = 5,
        evaluate_fn: Optional[Callable[[str], float]] = None,
    ) -> ToTNode:
        root = ToTNode(thought=query, depth=0, status=NodeStatus.ACTIVE)
        queue = [root]
        best_node = root
        best_score = 0.0

        while queue and root.depth < depth:
            node = queue.pop(0)

            candidates = await self._generate_candidates(node.thought, n=branching)

            for candidate in candidates:
                child = ToTNode(
                    thought=candidate,
                    parent=node,
                    depth=node.depth + 1,
                )

                if evaluate_fn:
                    child.score = await evaluate_fn(candidate)
                else:
                    child.score = 0.5

                node.add_child(child)

                if child.score > best_score:
                    best_score = child.score
                    best_node = child

            node.children.sort(key=lambda x: x.score, reverse=True)
            node.children = node.children[:branching]

            queue.extend(node.children[:branching])

        return best_node

    async def _generate_candidates(self, thought: str, n: int) -> list[str]:
        if not self.llm_client:
            return [f"{thought} (branch {i})" for i in range(n)]

        prompt = f"Generate {n} different reasoning approaches for: {thought}"
        response = await self.llm_client.generate(prompt)

        candidates = [c.strip() for c in response.split("\n") if c.strip()]
        return candidates[:n]
