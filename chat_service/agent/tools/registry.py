"""Dynamic tool registry with decorator-based registration."""
from __future__ import annotations

from typing import Callable

import structlog

log = structlog.get_logger()

_registry: dict[str, dict] = {}


def register_tool(name: str, description: str = ""):
    """Decorator to register a tool function."""

    def decorator(fn: Callable):
        _registry[name] = {"fn": fn, "description": description, "name": name}
        log.debug("tool_registered", name=name)
        return fn

    return decorator


def get_tool(name: str) -> Callable | None:
    """Look up a registered tool by name."""
    entry = _registry.get(name)
    return entry["fn"] if entry else None


def list_tools() -> list[dict]:
    """Return metadata for all registered tools."""
    return [{"name": v["name"], "description": v["description"]} for v in _registry.values()]
