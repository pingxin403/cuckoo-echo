from typing import Any
from pydantic import BaseModel
import asyncio
import json


class MCPResource(BaseModel):
    uri: str
    name: str
    mime_type: str | None = None


class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = {}


class MCPConnection(BaseModel):
    server_id: str
    server_url: str
    status: str = "disconnected"
    tools: list[MCPTool] = []
    resources: list[MCPResource] = []


class MCPClient:
    def __init__(self):
        self._connections: dict[str, MCPConnection] = {}
        self._message_handlers: dict[str, asyncio.Queue] = {}

    async def connect(
        self,
        server_id: str,
        server_url: str,
    ) -> MCPConnection:
        connection = MCPConnection(
            server_id=server_id,
            server_url=server_url,
            status="connecting",
        )
        
        try:
            await self._establish_connection(connection)
            connection.status = "connected"
        except Exception as e:
            connection.status = f"error: {str(e)}"
        
        self._connections[server_id] = connection
        return connection

    async def disconnect(self, server_id: str) -> bool:
        if server_id in self._connections:
            del self._connections[server_id]
            return True
        return False

    async def list_tools(self, server_id: str) -> list[MCPTool]:
        conn = self._connections.get(server_id)
        if conn and conn.status == "connected":
            return conn.tools
        return []

    async def list_resources(self, server_id: str) -> list[MCPResource]:
        conn = self._connections.get(server_id)
        if conn and conn.status == "connected":
            return conn.resources
        return []

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        conn = self._connections.get(server_id)
        if not conn or conn.status != "connected":
            raise ValueError(f"Not connected to server: {server_id}")
        
        tool = next((t for t in conn.tools if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        return await self._invoke_mcp_tool(conn, tool_name, arguments)

    async def read_resource(self, server_id: str, uri: str) -> Any:
        conn = self._connections.get(server_id)
        if not conn or conn.status != "connected":
            raise ValueError(f"Not connected to server: {server_id}")
        
        resource = next((r for r in conn.resources if r.uri == uri), None)
        if not resource:
            raise ValueError(f"Resource not found: {uri}")
        
        return await self._read_mcp_resource(conn, uri)

    def get_connection_status(self, server_id: str) -> str | None:
        conn = self._connections.get(server_id)
        return conn.status if conn else None

    def list_servers(self) -> list[MCPConnection]:
        return list(self._connections.values())

    async def _establish_connection(self, connection: MCPConnection) -> None:
        await asyncio.sleep(0.1)
        connection.tools = [
            MCPTool(
                name="sample_tool",
                description="Sample MCP tool",
                input_schema={"type": "object", "properties": {}},
            )
        ]
        connection.resources = [
            MCPResource(
                uri="sample://resource",
                name="Sample Resource",
            )
        ]

    async def _invoke_mcp_tool(self, connection: MCPConnection, tool_name: str, arguments: dict[str, Any]) -> Any:
        return {"status": "success", "tool": tool_name}

    async def _read_mcp_resource(self, connection: MCPConnection, uri: str) -> Any:
        return {"content": "resource data"}


_global_mcp_client = MCPClient()


def get_mcp_client() -> MCPClient:
    return _global_mcp_client