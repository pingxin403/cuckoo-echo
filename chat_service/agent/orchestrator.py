"""Multi-agent orchestration with task decomposition and delegation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    EVENT = "event"


@dataclass
class AgentTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: str = ""
    description: str = ""
    status: str = "pending"
    assigned_agent: str | None = None
    result: Any | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


@dataclass
class RoleRegistry:
    """Registry for agent roles and capabilities."""

    _roles: dict[str, dict[str, Any]] = field(default_factory=dict)

    def register_role(self, role: str, capabilities: list[str], priority: int = 0) -> None:
        self._roles[role] = {
            "capabilities": capabilities,
            "priority": priority,
        }

    def get_capabilities(self, role: str) -> list[str]:
        return self._roles.get(role, {}).get("capabilities", [])

    def get_role_for_task(self, task_type: str) -> str | None:
        for role, info in self._roles.items():
            if task_type in info.get("capabilities", []):
                return role
        return None

    def list_roles(self) -> list[str]:
        return list(self._roles.keys())


class MultiAgentOrchestrator:
    """Orchestrates multiple agents for complex tasks."""

    def __init__(self):
        self.role_registry = RoleRegistry()
        self._tasks: dict[str, AgentTask] = {}
        self._agents: dict[str, Any] = {}
        self._results_callback: Callable[[str, Any], None] | None = None
        self._setup_default_roles()

    def _setup_default_roles(self) -> None:
        self.role_registry.register_role(
            "router",
            ["route", "classify", "escalate"],
            priority=10,
        )
        self.role_registry.register_role(
            "rag_specialist",
            ["search", "retrieve", "cite"],
            priority=5,
        )
        self.role_registry.register_role(
            "tool_executor",
            ["execute", "call_api", "database"],
            priority=5,
        )
        self.role_registry.register_role(
            "generalist",
            ["respond", "explain", "summarize"],
            priority=1,
        )

    def register_agent(self, agent_id: str, role: str, agent: Any) -> None:
        self._agents[agent_id] = {
            "role": role,
            "agent": agent,
            "status": "available",
        }
        logger.info("agent_registered", agent_id=agent_id, role=role)

    def _create_task(self, task_type: str, description: str) -> AgentTask:
        task = AgentTask(task_type=task_type, description=description)
        self._tasks[task.task_id] = task
        return task

    async def decompose_task(self, user_query: str) -> list[AgentTask]:
        """Break down a complex query into sub-tasks."""
        tasks = []
        words = user_query.lower()

        if any(k in words for k in ["search", "find", "look", "查询", "搜索"]):
            task = self._create_task("rag_specialist", f"Search for: {user_query}")
            tasks.append(task)

        if any(k in words for k in ["order", "status", "refund", "订单", "退款"]):
            task = self._create_task("tool_executor", f"Execute tool for: {user_query}")
            tasks.append(task)

        if any(k in words for k in ["explain", "what", "how", "why", "解释"]):
            task = self._create_task("generalist", f"Explain: {user_query}")
            tasks.append(task)

        if not tasks:
            task = self._create_task("generalist", f"Respond to: {user_query}")
            tasks.append(task)

        return tasks

    async def delegate_task(
        self, task: AgentTask, available_agents: list[str]
    ) -> str | None:
        """Assign a task to an available agent based on role."""
        target_role = self.role_registry.get_role_for_task(task.task_type)

        for agent_id in available_agents:
            agent_info = self._agents.get(agent_id)
            if agent_info and agent_info["status"] == "available":
                if target_role is None or agent_info["role"] == target_role:
                    task.assigned_agent = agent_id
                    task.status = "assigned"
                    agent_info["status"] = "busy"
                    logger.info(
                        "task_delegated",
                        task_id=task.task_id,
                        agent_id=agent_id,
                        role=agent_info["role"],
                    )
                    return agent_id

        fallback_agents = [
            aid for aid in available_agents
            if self._agents[aid]["status"] == "available"
        ]
        if fallback_agents:
            task.assigned_agent = fallback_agents[0]
            task.status = "assigned"
            self._agents[fallback_agents[0]]["status"] = "busy"
            return fallback_agents[0]

        return None

    async def aggregate_results(
        self, results: list[Any], aggregation_strategy: str = "concat"
    ) -> str:
        """Combine results from multiple agents."""
        if aggregation_strategy == "concat":
            combined = "\n\n".join(str(r) for r in results if r)
            return combined
        elif aggregation_strategy == "best":
            return str(max(results, key=lambda x: len(str(x)))) if results else ""
        return str(results[0]) if results else ""

    def mark_agent_available(self, agent_id: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id]["status"] = "available"
            logger.info("agent_available", agent_id=agent_id)

    def get_task_status(self, task_id: str) -> AgentTask | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[AgentTask]:
        return list(self._tasks.values())

    async def execute_workflow(
        self,
        user_query: str,
        available_agents: list[str],
        aggregation_strategy: str = "concat",
    ) -> tuple[str, list[AgentTask]]:
        """Execute a complete multi-agent workflow."""
        sub_tasks = await self.decompose_task(user_query)
        results = []

        for task in sub_tasks:
            agent_id = await self.delegate_task(task, available_agents)
            if agent_id is None:
                task.status = "no_agent"
                continue

            agent_info = self._agents[agent_id]
            agent = agent_info["agent"]

            try:
                if hasattr(agent, "execute_task"):
                    result = await agent.execute_task(task.description)
                else:
                    result = f"Agent {agent_id} processed: {task.description}"

                task.result = result
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                results.append(result)

                self.mark_agent_available(agent_id)

            except Exception as e:
                task.status = "failed"
                task.result = str(e)
                logger.error(
                    "task_execution_failed",
                    task_id=task.task_id,
                    agent_id=agent_id,
                    error=str(e),
                )

        final_response = await self.aggregate_results(results, aggregation_strategy)
        return final_response, sub_tasks


orchestrator = MultiAgentOrchestrator()