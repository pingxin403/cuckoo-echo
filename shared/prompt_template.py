from typing import Any, Callable
from pydantic import BaseModel
from datetime import datetime
import re


class PromptTemplate(BaseModel):
    id: str
    name: str
    template: str
    variables: list[str] = []
    version: int = 1
    created_at: datetime
    updated_at: datetime


class TemplateEngine:
    def __init__(self):
        self._templates: dict[str, PromptTemplate] = {}
        self._filters: dict[str, Callable] = {
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "capitalize": lambda x: str(x).capitalize(),
            "default": lambda x, default="": x or default,
        }

    def create(
        self,
        name: str,
        template: str,
        variables: list[str] | None = None,
    ) -> PromptTemplate:
        extracted_vars = self._extract_variables(template)
        tmpl = PromptTemplate(
            id=f"tpl_{datetime.now().timestamp()}",
            name=name,
            template=template,
            variables=variables or extracted_vars,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self._templates[name] = tmpl
        return tmpl

    def render(self, name: str, context: dict[str, Any]) -> str:
        tmpl = self._templates.get(name)
        if not tmpl:
            raise ValueError(f"Template not found: {name}")
        
        return self._render_string(tmpl.template, context)

    def _extract_variables(self, template: str) -> list[str]:
        var_pattern = r"\{\{([^}]+)\}\}"
        matches = re.findall(var_pattern, template)
        return list(set(matches))

    def _render_string(self, template: str, context: dict[str, Any]) -> str:
        result = template
        
        if_blocks = re.findall(r"\{% if ([^%]+) %\}(.*?)\{% endif %}", template, re.DOTALL)
        for condition, content in if_blocks:
            try:
                if self._eval_condition(condition.strip(), context):
                    result = result.replace(f"{{% if {condition} %}}{content}{{% endif %}}", content)
                else:
                    result = result.replace(f"{{% if {condition} %}}{content}{{% endif %}}", "")
            except Exception:
                pass
        
        for_loop_pattern = r"\{% for ([^%]+) in ([^%]+) %\}(.*?)\{% endfor %}"
        for_match = re.search(for_loop_pattern, template)
        if for_match:
            item_var, list_var, loop_content = for_match.groups()
            items = context.get(list_var.strip(), [])
            if isinstance(items, list):
                loop_result = "".join(
                    self._render_string(loop_content, {**context, item_var.strip(): item})
                    for item in items
                )
                result = re.sub(for_loop_pattern, loop_result, result, flags=re.DOTALL)
        
        var_pattern = r"\{\{([^}]+)\}\}"
        for match in re.finditer(var_pattern, result):
            var_path = match.group(1).strip()
            value = self._get_nested_value(context, var_path)
            if value is not None:
                result = result.replace(match.group(0), str(value))
        
        return result

    def _eval_condition(self, condition: str, context: dict[str, Any]) -> bool:
        import operator
        ops = {"==": operator.eq, "!=": operator.ne, ">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le}
        
        for op_name, op_func in ops.items():
            if op_name in condition:
                parts = condition.split(op_name)
                if len(parts) == 2:
                    left = self._get_nested_value(context, parts[0].strip())
                    right = parts[1].strip().strip('"\'')
                    try:
                        return op_func(left, right)
                    except Exception:
                        return False
        return bool(context.get(condition.strip()))

    def _get_nested_value(self, context: dict[str, Any], path: str) -> Any:
        keys = path.split(".")
        value = context
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


_global_engine = TemplateEngine()


def get_template_engine() -> TemplateEngine:
    return _global_engine


def create_template(name: str, template: str) -> PromptTemplate:
    return _global_engine.create(name, template)


def render_template(name: str, context: dict[str, Any]) -> str:
    return _global_engine.render(name, context)