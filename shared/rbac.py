"""Role-Based Access Control for enterprise deployments."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Optional, Callable, Any


class Resource(Enum):
    CONVERSATIONS = "conversations"
    KNOWLEDGE = "knowledge"
    REPORTS = "reports"
    SETTINGS = "settings"
    AGENTS = "agents"
    TENANTS = "tenants"
    BILLING = "billing"


class Action(Enum):
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    EXPORT = "export"
    MANAGE = "manage"


class Scope(Enum):
    ALL = "all"
    DEPARTMENT = "department"
    OWN = "own"


class Role(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    TEAM_LEAD = "team_lead"
    AGENT = "agent"
    VIEWER = "viewer"
    CUSTOM = "custom"


PERMISSIONS = {
    Role.SUPER_ADMIN: [
        (Resource.CONVERSATIONS, Action.VIEW, Scope.ALL),
        (Resource.CONVERSATIONS, Action.CREATE, Scope.ALL),
        (Resource.CONVERSATIONS, Action.EDIT, Scope.ALL),
        (Resource.CONVERSATIONS, Action.DELETE, Scope.ALL),
        (Resource.CONVERSATIONS, Action.EXPORT, Scope.ALL),
        (Resource.CONVERSATIONS, Action.MANAGE, Scope.ALL),
        (Resource.KNOWLEDGE, Action.VIEW, Scope.ALL),
        (Resource.KNOWLEDGE, Action.CREATE, Scope.ALL),
        (Resource.KNOWLEDGE, Action.EDIT, Scope.ALL),
        (Resource.KNOWLEDGE, Action.DELETE, Scope.ALL),
        (Resource.KNOWLEDGE, Action.EXPORT, Scope.ALL),
        (Resource.KNOWLEDGE, Action.MANAGE, Scope.ALL),
        (Resource.REPORTS, Action.VIEW, Scope.ALL),
        (Resource.REPORTS, Action.CREATE, Scope.ALL),
        (Resource.REPORTS, Action.EDIT, Scope.ALL),
        (Resource.REPORTS, Action.DELETE, Scope.ALL),
        (Resource.REPORTS, Action.EXPORT, Scope.ALL),
        (Resource.REPORTS, Action.MANAGE, Scope.ALL),
        (Resource.SETTINGS, Action.VIEW, Scope.ALL),
        (Resource.SETTINGS, Action.CREATE, Scope.ALL),
        (Resource.SETTINGS, Action.EDIT, Scope.ALL),
        (Resource.SETTINGS, Action.DELETE, Scope.ALL),
        (Resource.SETTINGS, Action.EXPORT, Scope.ALL),
        (Resource.SETTINGS, Action.MANAGE, Scope.ALL),
        (Resource.AGENTS, Action.VIEW, Scope.ALL),
        (Resource.AGENTS, Action.CREATE, Scope.ALL),
        (Resource.AGENTS, Action.EDIT, Scope.ALL),
        (Resource.AGENTS, Action.DELETE, Scope.ALL),
        (Resource.AGENTS, Action.EXPORT, Scope.ALL),
        (Resource.AGENTS, Action.MANAGE, Scope.ALL),
        (Resource.TENANTS, Action.VIEW, Scope.ALL),
        (Resource.TENANTS, Action.CREATE, Scope.ALL),
        (Resource.TENANTS, Action.EDIT, Scope.ALL),
        (Resource.TENANTS, Action.DELETE, Scope.ALL),
        (Resource.TENANTS, Action.EXPORT, Scope.ALL),
        (Resource.TENANTS, Action.MANAGE, Scope.ALL),
        (Resource.BILLING, Action.VIEW, Scope.ALL),
        (Resource.BILLING, Action.CREATE, Scope.ALL),
        (Resource.BILLING, Action.EDIT, Scope.ALL),
        (Resource.BILLING, Action.DELETE, Scope.ALL),
        (Resource.BILLING, Action.EXPORT, Scope.ALL),
        (Resource.BILLING, Action.MANAGE, Scope.ALL),
    ],
    Role.ADMIN: [
        (Resource.CONVERSATIONS, Action.MANAGE, Scope.ALL),
        (Resource.KNOWLEDGE, Action.MANAGE, Scope.DEPARTMENT),
        (Resource.REPORTS, Action.VIEW, Scope.ALL),
        (Resource.SETTINGS, Action.MANAGE, Scope.DEPARTMENT),
    ],
    Role.TEAM_LEAD: [
        (Resource.CONVERSATIONS, Action.VIEW, Scope.DEPARTMENT),
        (Resource.CONVERSATIONS, Action.EDIT, Scope.DEPARTMENT),
        (Resource.KNOWLEDGE, Action.VIEW, Scope.DEPARTMENT),
        (Resource.KNOWLEDGE, Action.CREATE, Scope.DEPARTMENT),
        (Resource.REPORTS, Action.VIEW, Scope.DEPARTMENT),
    ],
    Role.AGENT: [
        (Resource.CONVERSATIONS, Action.VIEW, Scope.OWN),
        (Resource.CONVERSATIONS, Action.EDIT, Scope.OWN),
        (Resource.KNOWLEDGE, Action.VIEW, Scope.ALL),
    ],
    Role.VIEWER: [
        (Resource.CONVERSATIONS, Action.VIEW, Scope.OWN),
        (Resource.REPORTS, Action.VIEW, Scope.OWN),
    ],
    Role.CUSTOM: [],
}


@dataclass
class RBACContext:
    user_id: str
    role: Role
    tenant_id: str
    department_id: Optional[str] = None
    custom_permissions: list = field(default_factory=lambda: [])

    def has_permission(self, resource: Resource, action: Action, scope: Scope = Scope.OWN) -> bool:
        if self.role == Role.SUPER_ADMIN:
            return True
        
        if self.role == Role.CUSTOM:
            perms = self.custom_permissions
        else:
            perms = PERMISSIONS.get(self.role, [])
        
        for r, a, s in perms:
            if r == resource and a == action:
                if s == Scope.ALL:
                    return True
                if s == scope:
                    return True
                if s == Scope.DEPARTMENT and self.department_id:
                    return True
        return False

    def get_allowed_resources(self, action: Action) -> list:
        if self.role == Role.SUPER_ADMIN:
            return list(Resource)
        
        perms = PERMISSIONS.get(self.role, []) + self.custom_permissions
        resources = set()
        for r, a, _ in perms:
            if a == action:
                resources.add(r)
        return list(resources)


def check_permission(resource: Resource, action: Action, scope: Scope = Scope.OWN) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            rbac = kwargs.get("_rbac")
            if rbac and not rbac.has_permission(resource, action, scope):
                raise PermissionError(f"No permission: {action.value} {resource.value}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


@dataclass
class AuditLog:
    user_id: str
    action: Action
    resource: Resource
    resource_id: str
    tenant_id: str
    timestamp: str = ""
    details: Optional[dict] = None


class AuditLogger:
    def __init__(self) -> None:
        self.logs: list = []

    def log(self, audit_log: AuditLog) -> None:
        self.logs.append(audit_log)

    def get_logs(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        resource: Optional[Resource] = None,
    ) -> list:
        filtered = [l for l in self.logs if l.tenant_id == tenant_id]
        if user_id:
            filtered = [l for l in filtered if l.user_id == user_id]
        if resource:
            filtered = [l for l in filtered if l.resource == resource]
        return filtered


audit_logger = AuditLogger()