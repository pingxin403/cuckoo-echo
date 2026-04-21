"""Plugin system for extensible functionality."""

from __future__ import annotations

import importlib.util
import json
import structlog
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

log = structlog.get_logger()


@dataclass
class PluginManifest:
    """Plugin manifest definition."""
    name: str
    version: str
    plugin_type: str
    description: str
    entry: str
    permissions: list[str]
    author: Optional[str] = None
    tenant_id: Optional[str] = None


@dataclass
class RegisteredPlugin:
    """A registered and loaded plugin."""
    manifest: PluginManifest
    module: Any
    enabled: bool = True


class PluginRegistry:
    """Central plugin registry for the application."""

    def __init__(self):
        self._plugins: dict[str, RegisteredPlugin] = {}
        self._tools: dict[str, Callable] = {}
        self._triggers: dict[str, list[Callable]] = {}

    def register(self, manifest: PluginManifest, module: Any) -> None:
        """Register a plugin."""
        self._plugins[manifest.name] = RegisteredPlugin(
            manifest=manifest,
            module=module,
        )

        if hasattr(module, "register_tools"):
            module.register_tools(self._tools)

        if hasattr(module, "register_triggers"):
            module.register_triggers(self._triggers)

        log.info("plugin_registered", name=manifest.name, type=manifest.plugin_type)

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def get_trigger_handlers(self, event_type: str) -> list[Callable]:
        """Get trigger handlers for an event type."""
        return self._triggers.get(event_type, [])

    def list_plugins(self) -> list[PluginManifest]:
        """List all registered plugins."""
        return [p.manifest for p in self._plugins.values()]

    def enable(self, name: str) -> bool:
        """Enable a plugin."""
        if name in self._plugins:
            self._plugins[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a plugin."""
        if name in self._plugins:
            self._plugins[name].enabled = False
            return True
        return False


_global_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _global_registry


def load_plugin_from_manifest(manifest_path: Path) -> PluginManifest:
    """Load a plugin from its manifest file."""
    with open(manifest_path) as f:
        data = json.load(f)

    return PluginManifest(
        name=data["name"],
        version=data["version"],
        plugin_type=data["type"],
        description=data.get("description", ""),
        entry=data.get("entry", "index.py"),
        permissions=data.get("permissions", []),
        author=data.get("author"),
    )


def load_plugin_module(manifest: PluginManifest, plugin_dir: Path) -> Any:
    """Load a plugin's Python module."""
    entry_file = plugin_dir / manifest.entry
    if not entry_file.exists():
        raise FileNotFoundError(f"Plugin entry file not found: {entry_file}")

    spec = importlib.util.spec_from_file_location(manifest.name, entry_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


async def execute_tool(
    tool_name: str,
    **kwargs: Any,
) -> Any:
    """Execute a registered tool."""
    registry = get_plugin_registry()
    tool = registry.get_tool(tool_name)

    if not tool:
        raise ValueError(f"Tool not found: {tool_name}")

    if asyncio.iscoroutinefunction(tool):
        return await tool(**kwargs)
    return tool(**kwargs)


async def trigger_event(
    event_type: str,
    **kwargs: Any,
) -> list[Any]:
    """Trigger an event and execute all registered handlers."""
    registry = get_plugin_registry()
    handlers = registry.get_trigger_handlers(event_type)

    results = []
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)
            results.append(result)
        except Exception as e:
            log.error("trigger_handler_error", event=event_type, handler=handler.__name__, error=str(e))

    return results


import asyncio