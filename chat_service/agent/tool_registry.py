from typing import Any, Callable, Coroutine
from pydantic import BaseModel
from enum import Enum


class ToolType(str, Enum):
    API = "api"
    FUNCTION = "function"
    PROMPT = "prompt"
    MCP = "mcp"


class ToolDefinition(BaseModel):
    name: str
    description: str
    tool_type: ToolType
    parameters: dict[str, Any] = {}
    handler: Callable | None = None
    mcp_server: str | None = None
    enabled: bool = True


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._tool_handlers: dict[str, Callable] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        tool_type: ToolType = ToolType.FUNCTION,
        parameters: dict[str, Any] | None = None,
        handler: Callable | None = None,
        mcp_server: str | None = None,
    ) -> ToolDefinition:
        tool = ToolDefinition(
            name=name,
            description=description,
            tool_type=tool_type,
            parameters=parameters or {},
            handler=handler,
            mcp_server=mcp_server,
        )
        self._tools[name] = tool
        
        if handler:
            self._tool_handlers[name] = handler
        
        return tool

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self, enabled_only: bool = True) -> list[ToolDefinition]:
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return tools

    def enable_tool(self, name: str) -> bool:
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False

    def disable_tool(self, name: str) -> bool:
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    def unregister_tool(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            self._tool_handlers.pop(name, None)
            return True
        return False


_global_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _global_registry