"""Multi-agent orchestration with task decomposition and delegation."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import structlog

from chat_service.agent.role_registry import RoleRegistry

logger = structlog.get_logger(__name__)


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
    trace_id: str | None = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskMetrics:
    total_delegations: int = 0
    total_latency_ms: float = 0.0
    failed_tasks: int = 0
    successful_tasks: int = 0


class MultiAgentOrchestrator:
    """Orchestrates multiple agents for complex tasks."""

    def __init__(self):
        self.role_registry = RoleRegistry()
        self._tasks: dict[str, AgentTask] = {}
        self._agents: dict[str, Any] = {}
        self._results_callback: Callable[[str, Any], None] | None = None
        self._metrics = TaskMetrics()
        self._default_timeout = 30.0
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

    def _create_task(self, task_type: str, description: str, trace_id: str | None = None) -> AgentTask:
        task = AgentTask(task_type=task_type, description=description, trace_id=trace_id)
        self._tasks[task.task_id] = task
        return task

    async def decompose_task(self, user_query: str) -> list[AgentTask]:
        """Break down a complex query into sub-tasks."""
        tasks = []
        words = user_query.lower()
        trace_id = str(uuid.uuid4())

        if any(k in words for k in ["search", "find", "look", "查询", "搜索"]):
            task = self._create_task("rag_specialist", f"Search for: {user_query}", trace_id)
            tasks.append(task)

        if any(k in words for k in ["order", "status", "refund", "订单", "退款"]):
            task = self._create_task("tool_executor", f"Execute tool for: {user_query}", trace_id)
            tasks.append(task)

        if any(k in words for k in ["explain", "what", "how", "why", "解释"]):
            task = self._create_task("generalist", f"Explain: {user_query}", trace_id)
            tasks.append(task)

        if not tasks:
            task = self._create_task("generalist", f"Respond to: {user_query}", trace_id)
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
                        trace_id=task.trace_id,
                    )
                    return agent_id

        fallback_agents = [
            aid for aid in available_agents
            if self._agents.get(aid, {}).get("status") == "available"
        ]
        if fallback_agents:
            task.assigned_agent = fallback_agents[0]
            task.status = "assigned"
            self._agents[fallback_agents[0]]["status"] = "busy"
            return fallback_agents[0]

        return None

    async def execute_with_retry(
        self, agent, task: AgentTask, timeout: float | None = None
    ) -> Any:
        """Execute task with retry and timeout handling."""
        timeout = timeout or self._default_timeout
        last_error = None

        for attempt in range(task.max_retries + 1):
            task.retry_count = attempt
            start_time = time.time()

            try:
                if hasattr(agent, "execute_task"):
                    result = await asyncio.wait_for(
                        agent.execute_task(task.description),
                        timeout=timeout,
                    )
                else:
                    result = f"Agent processed: {task.description}"

                latency_ms = (time.time() - start_time) * 1000
                self._metrics.total_delegations += 1
                self._metrics.total_latency_ms += latency_ms
                self._metrics.successful_tasks += 1

                logger.info(
                    "task_executed",
                    task_id=task.task_id,
                    latency_ms=round(latency_ms, 2),
                    attempt=attempt + 1,
                    trace_id=task.trace_id,
                )
                return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {timeout}s"
                logger.warning(
                    "task_timeout",
                    task_id=task.task_id,
                    timeout=timeout,
                    attempt=attempt + 1,
                    trace_id=task.trace_id,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "task_retry",
                    task_id=task.task_id,
                    error=str(e),
                    attempt=attempt + 1,
                    trace_id=task.trace_id,
                )

            if attempt < task.max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))

        self._metrics.failed_tasks += 1
        return f"Task failed after {task.max_retries + 1} attempts: {last_error}"

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

    def get_metrics(self) -> dict[str, Any]:
        """Get orchestration metrics."""
        return {
            "total_delegations": self._metrics.total_delegations,
            "avg_latency_ms": (
                self._metrics.total_latency_ms / self._metrics.total_delegations
                if self._metrics.total_delegations > 0
                else 0
            ),
            "failed_tasks": self._metrics.failed_tasks,
            "successful_tasks": self._metrics.successful_tasks,
            "success_rate": (
                self._metrics.successful_tasks / max(self._metrics.total_delegations, 1)
            ),
        }

    async def execute_workflow(
        self,
        user_query: str,
        available_agents: list[str],
        aggregation_strategy: str = "concat",
    ) -> tuple[str, list[AgentTask]]:
        """Execute a complete multi-agent workflow."""
        sub_tasks = await self.decompose_task(user_query)
        results = []
        trace_id = str(uuid.uuid4())

        for task in sub_tasks:
            task.trace_id = trace_id
            agent_id = await self.delegate_task(task, available_agents)
            if agent_id is None:
                task.status = "no_agent"
                logger.warning("no_agent_available", task_id=task.task_id, trace_id=trace_id)
                continue

            agent_info = self._agents[agent_id]
            agent = agent_info["agent"]

            result = await self.execute_with_retry(agent, task)

            task.result = result
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            results.append(result)

            self.mark_agent_available(agent_id)

        final_response = await self.aggregate_results(results, aggregation_strategy)
        logger.info(
            "workflow_completed",
            trace_id=trace_id,
            tasks=len(sub_tasks),
            successful=sum(1 for t in sub_tasks if t.status == "completed"),
        )
        return final_response, sub_tasks


orchestrator = MultiAgentOrchestrator()