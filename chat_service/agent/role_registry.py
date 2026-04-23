"""Role registry for agent role management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RoleRegistry:
    """Registry for agent roles and capabilities."""

    _roles: dict[str, dict[str, Any]] = field(default_factory=dict)

    def register_role(self, role: str, capabilities: list[str], priority: int = 0) -> None:
        """Register a role with its capabilities."""
        self._roles[role] = {
            "capabilities": capabilities,
            "priority": priority,
        }
        logger.info("role_registered", role=role, capabilities=capabilities, priority=priority)

    def get_capabilities(self, role: str) -> list[str]:
        """Get capabilities for a role."""
        return self._roles.get(role, {}).get("capabilities", [])

    def get_role_for_task(self, task_type: str) -> str | None:
        """Find the best role for a task type."""
        for role, info in self._roles.items():
            if task_type in info.get("capabilities", []):
                return role
        return None

    def list_roles(self) -> list[str]:
        """List all registered roles."""
        return list(self._roles.keys())

    def get_role_priority(self, role: str) -> int:
        """Get priority for a role."""
        return self._roles.get(role, {}).get("priority", 0)


role_registry = RoleRegistry()