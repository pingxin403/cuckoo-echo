"""Prompt template engine with variable interpolation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptTemplate:
    """Template engine with {{variable}}, {% if %}, {% for %} support."""

    template: str = ""
    _var_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r"\{\{(\w+)\}\}")
    )
    _if_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r"\{% if (\w+) %\}(.*?)\{% endif %\}", re.DOTALL)
    )
    _for_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r"\{% for (\w+) in (\w+) %\}(.*?)\{% endfor %\}", re.DOTALL)
    )

    def render(self, context: dict[str, Any]) -> str:
        """Render template with variables from context."""
        result = self.template

        result = self._render_for_loops(result, context)
        result = self._render_if_blocks(result, context)
        result = self._render_variables(result, context)

        return result.strip()

    def _render_variables(self, text: str, context: dict[str, Any]) -> str:
        """Replace {{variable}} placeholders."""
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            value = context.get(var_name, "")
            return str(value) if value is not None else ""

        return self._var_pattern.sub(replace_var, text)

    def _render_if_blocks(self, text: str, context: dict[str, Any]) -> str:
        """Process {% if condition %} blocks."""
        def replace_if(match: re.Match) -> str:
            condition = match.group(1)
            body = match.group(2)
            if context.get(condition, False):
                return self._render_variables(body, context)
            return ""

        return self._if_pattern.sub(replace_if, text)

    def _render_for_loops(self, text: str, context: dict[str, Any]) -> str:
        """Process {% for item in items %} blocks."""
        def replace_for(match: re.Match) -> str:
            item_name = match.group(1)
            list_name = match.group(2)
            body = match.group(3)
            items = context.get(list_name, [])
            results = []
            for item in items:
                loop_context = context.copy()
                loop_context[item_name] = item
                results.append(self._render_variables(body, loop_context))
            return "\n".join(results)

        return self._for_pattern.sub(replace_for, text)


@dataclass
class PromptTemplateStore:
    """Storage for prompt templates with versioning."""

    _templates: dict[str, PromptTemplate] = field(default_factory=dict)
    _versions: dict[str, list[str]] = field(default_factory=dict)

    def add(self, name: str, template: str, version: str = "v1") -> None:
        """Add a template with version."""
        key = f"{name}:{version}"
        self._templates[key] = PromptTemplate(template=template)
        if name not in self._versions:
            self._versions[name] = []
        if version not in self._versions[name]:
            self._versions[name].append(version)

    def get(self, name: str, version: str = "v1") -> PromptTemplate | None:
        """Get a template by name and version."""
        key = f"{name}:{version}"
        return self._templates.get(key)

    def list_versions(self, name: str) -> list[str]:
        """List all versions of a template."""
        return self._versions.get(name, [])