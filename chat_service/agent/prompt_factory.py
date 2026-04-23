"""Prompt factory for role-based generation."""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from typing import Any

from chat_service.agent.prompt_template import PromptTemplate, PromptTemplateStore

logger = structlog.get_logger(__name__)


SYSTEM_PROMPTS = {
    "router": "Determine user intent and route to appropriate handler: {{task_description}}",
    "rag_specialist": "Search knowledge base and provide accurate citations for: {{query}}",
    "generalist": "Provide a clear, helpful response to: {{user_query}}",
    "tool_executor": "Execute the requested tool action: {{action}}",
}


@dataclass
class FewShotExample:
    """Example for few-shot prompting."""
    input_text: str
    output_text: str
    relevance_score: float = 1.0


@dataclass
class PromptFactory:
    """Factory for generating role-based prompts."""

    _role_prompts: dict[str, str] = field(default_factory=dict)
    _few_shot_examples: dict[str, list[FewShotExample]] = field(default_factory=dict)
    _template_store: PromptTemplateStore = field(default_factory=PromptTemplateStore)

    def __post_init__(self) -> None:
        self._role_prompts = SYSTEM_PROMPTS.copy()
        self._setup_default_examples()

    def _setup_default_examples(self) -> None:
        self._few_shot_examples = {
            "router": [
                FewShotExample(
                    input_text="Where is my order?",
                    output_text="Intent: order_status, Category: logistics",
                ),
                FewShotExample(
                    input_text="How much is the premium plan?",
                    output_text="Intent: pricing, Category: billing",
                ),
            ],
            "rag_specialist": [
                FewShotExample(
                    input_text="What is the return policy?",
                    output_text="Return within 30 days. Items must be unused.",
                ),
            ],
        }

    def register_role_prompt(self, role: str, template: str) -> None:
        """Register a prompt template for a role."""
        self._role_prompts[role] = template
        logger.info("role_prompt_registered", role=role)

    def add_few_shot_example(
        self, role: str, input_text: str, output_text: str, relevance_score: float = 1.0
    ) -> None:
        """Add a few-shot example for a role."""
        if role not in self._few_shot_examples:
            self._few_shot_examples[role] = []
        self._few_shot_examples[role].append(
            FewShotExample(input_text=input_text, output_text=output_text, relevance_score=relevance_score)
        )

    def select_few_shot_examples(
        self, role: str, query: str, max_examples: int = 3
    ) -> list[FewShotExample]:
        """Select relevant few-shot examples based on query."""
        examples = self._few_shot_examples.get(role, [])
        if not examples:
            return []

        scored = []
        for ex in examples:
            relevance = 1.0 if ex.input_text.lower() in query.lower() else 0.5
            scored.append((ex, relevance * ex.relevance_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [ex for ex, _ in scored[:max_examples]]

    def create_prompt(
        self,
        role: str,
        context: dict[str, Any],
        include_cot: bool = False,
        include_few_shot: bool = True,
    ) -> str:
        """Create a prompt for a role with context."""
        template_str = self._role_prompts.get(role, self._role_prompts.get("generalist", ""))
        template = PromptTemplate(template=template_str)

        prompt_parts = []

        if include_few_shot:
            query = context.get("query", context.get("user_query", ""))
            examples = self.select_few_shot_examples(role, query)
            if examples:
                prompt_parts.append("Examples:")
                for ex in examples:
                    prompt_parts.append(f"Input: {ex.input_text}")
                    prompt_parts.append(f"Output: {ex.output_text}")
                prompt_parts.append("")

        if include_cot:
            prompt_parts.append("Think step by step before responding.")

        prompt_parts.append(template.render(context))

        logger.debug("prompt_created", role=role, parts=len(prompt_parts))
        return "\n".join(prompt_parts)

    def create_cot_prompt(
        self, role: str, context: dict[str, Any], reasoning_steps: int = 3
    ) -> str:
        """Create a chain-of-thought prompt."""
        steps = "\n".join(f"Step {i + 1}: " for i in range(reasoning_steps))
        cot_context = {**context, "reasoning_steps": steps}
        return self.create_prompt(role, cot_context, include_cot=True)


prompt_factory = PromptFactory()