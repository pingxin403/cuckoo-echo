from typing import Any, Callable, Coroutine
from pydantic import BaseModel
import asyncio
from datetime import datetime


class ToolExecution(BaseModel):
    tool_name: str
    parameters: dict[str, Any]
    result: Any | None = None
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None


class ToolExecutor:
    def __init__(self, registry=None):
        self.registry = registry
        self._execution_history: list[ToolExecution] = []

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        timeout: float = 30.0,
    ) -> ToolExecution:
        exec_record = ToolExecution(
            tool_name=tool_name,
            parameters=parameters,
            started_at=datetime.now(),
        )
        
        try:
            if self.registry:
                tool = self.registry.get_tool(tool_name)
                if not tool:
                    raise ValueError(f"Tool not found: {tool_name}")
                
                handler = self._get_handler(tool_name)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        result = await asyncio.wait_for(handler(**parameters), timeout=timeout)
                    else:
                        result = handler(**parameters)
                    exec_record.result = result
                else:
                    raise ValueError(f"No handler for tool: {tool_name}")
            else:
                raise ValueError("No registry configured")
                
        except Exception as e:
            exec_record.error = str(e)
        
        exec_record.completed_at = datetime.now()
        if exec_record.started_at and exec_record.completed_at:
            exec_record.duration_ms = int(
                (exec_record.completed_at - exec_record.started_at).total_seconds() * 1000
            )
        
        self._execution_history.append(exec_record)
        return exec_record

    async def execute_sequence(
        self,
        tools: list[tuple[str, dict[str, Any]]],
        stop_on_error: bool = True,
    ) -> list[ToolExecution]:
        results = []
        
        for tool_name, params in tools:
            result = await self.execute_tool(tool_name, params)
            results.append(result)
            
            if stop_on_error and result.error:
                break
        
        return results

    async def execute_parallel(
        self,
        tools: list[tuple[str, dict[str, Any]]],
    ) -> list[ToolExecution]:
        tasks = [
            self.execute_tool(tool_name, params)
            for tool_name, params in tools
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        executions = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                executions.append(ToolExecution(
                    tool_name=tools[i][0],
                    parameters=tools[i][1],
                    error=str(result),
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                ))
            else:
                executions.append(result)
        
        return executions

    def get_execution_history(self, limit: int = 100) -> list[ToolExecution]:
        return self._execution_history[-limit:]

    def _get_handler(self, tool_name: str) -> Callable | None:
        if self.registry and tool_name in self.registry._tool_handlers:
            return self.registry._tool_handlers[tool_name]
        return None
