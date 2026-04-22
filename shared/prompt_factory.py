from typing import Any
from pydantic import BaseModel
from datetime import datetime


class FewShotExample(BaseModel):
    input: str
    output: str
    score: float = 1.0


class PromptFactory:
    def __init__(self, template_engine=None):
        self.template_engine = template_engine
        self._fewshot_examples: dict[str, list[FewShotExample]] = {}

    def create_system_prompt(
        self,
        use_case: str,
        context: dict[str, Any],
    ) -> str:
        prompts = {
            "customer_support": self._customer_support_prompt,
            "technical_support": self._technical_support_prompt,
            "sales": self._sales_prompt,
            "general": self._general_prompt,
        }
        
        prompt_func = prompts.get(use_case, self._general_prompt)
        return prompt_func(context)

    def _customer_support_prompt(self, context: dict[str, Any]) -> str:
        name = context.get("user_name", "User")
        return f"""You are a helpful customer support agent. Be friendly, patient, and empathetic.

Current User: {name}

Guidelines:
- Acknowledge the user's concern
- Ask clarifying questions when needed
- Provide clear, actionable solutions
- End with a follow-up question"""

    def _technical_support_prompt(self, context: dict[str, Any]) -> str:
        return """You are a technical support specialist. 

Guidelines:
- Gather system information first
- Provide step-by-step solutions
- Include troubleshooting steps
- Ask for error messages verbatim"""

    def _sales_prompt(self, context: dict[str, Any]) -> str:
        return """You are a helpful sales assistant.

Guidelines:
- Understand the customer's needs first
- Highlight relevant product features
- Provide pricing information when asked
- Never be pushy"""

    def _general_prompt(self, context: dict[str, Any]) -> str:
        return """You are a helpful AI assistant.

Guidelines:
- Be clear and concise
- Provide accurate information
- Admit when you don't know"""

    def inject_context(
        self,
        base_prompt: str,
        context: dict[str, Any],
    ) -> str:
        context_parts = []
        
        if "user_info" in context:
            user_info = context["user_info"]
            context_parts.append(f"User: {user_info.get('name', 'Unknown')}")
        
        if "conversation_history" in context:
            history = context["conversation_history"]
            if history:
                recent = history[-3:]
                context_parts.append(f"Recent: {recent}")
        
        if "memory" in context:
            memory = context["memory"]
            if memory:
                context_parts.append(f"Context: {memory}")
        
        if context_parts:
            return f"{base_prompt}\n\n{' | '.join(context_parts)}"
        
        return base_prompt

    def add_fewshot_example(
        self,
        prompt_type: str,
        input_text: str,
        output_text: str,
    ) -> FewShotExample:
        example = FewShotExample(
            input=input_text,
            output=output_text,
        )
        
        if prompt_type not in self._fewshot_examples:
            self._fewshot_examples[prompt_type] = []
        
        self._fewshot_examples[prompt_type].append(example)
        return example

    def select_fewshot_examples(
        self,
        prompt_type: str,
        current_input: str,
        k: int = 3,
    ) -> list[FewShotExample]:
        if prompt_type not in self._fewshot_examples:
            return []
        
        examples = self._fewshot_examples[prompt_type]
        scored = [(ex, self._score_example(ex, current_input)) for ex in examples]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [ex for ex, _ in scored[:k]]

    def _score_example(self, example: FewShotExample, current_input: str) -> float:
        score = example.score
        
        if example.input.lower()[:50] == current_input.lower()[:50]:
            score += 0.5
        
        return score

    def build_cot_prompt(
        self,
        question: str,
        context: str | None = None,
    ) -> str:
        prompt = f"""Let's think step by step.

Question: {question}
"""
        
        if context:
            prompt += f"\nContext: {context}\n"
        
        prompt += "\nSteps:\n"
        
        return prompt


_global_factory = PromptFactory()


def get_prompt_factory() -> PromptFactory:
    return _global_factory