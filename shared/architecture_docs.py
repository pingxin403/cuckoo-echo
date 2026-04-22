"""Architecture documentation module."""

from __future__ import annotations
from typing import Any


SYSTEM_COMPONENTS = {
    "frontend": {
        "technology": "React SPA (Vite)",
        "features": ["WebSocket client", "State management (Zustand)"],
    },
    "api_gateway": {
        "technology": "FastAPI",
        "features": ["API Key + JWT", "Rate limiting", "Request routing"],
    },
    "services": {
        "chat_service": {"port": 8001, "protocols": ["gRPC", "HTTP"]},
        "ai_gateway": {"port": 8002, "protocols": ["HTTP", "WebSocket"]},
        "admin_service": {"port": 8000, "protocols": ["HTTP"]},
        "billing_service": {"port": 8003, "protocols": ["gRPC"]},
    },
    "data": {
        "PostgreSQL": "Primary data",
        "Redis": "Cache and sessions",
        "pgvector": "Semantic search",
        "S3": "File storage",
    },
}


API_ENDPOINTS = {
    "/v1/chat/completions": {"method": "POST", "description": "Stream chat responses"},
    "/v1/chat/history": {"method": "GET", "description": "Get conversation history"},
    "/v1/knowledge/search": {"method": "POST", "description": "Search knowledge base"},
    "/v1/agents": {"method": "GET", "description": "List AI agents"},
    "/v1/admin/users": {"method": "GET", "description": "List users (admin)"},
    "/v1/admin/conversations": {"method": "GET", "description": "List conversations"},
    "/v1/admin/metrics": {"method": "GET", "description": "Get metrics"},
}


DATABASE_SCHEMA = {
    "organizations": ["id", "name", "settings", "created_at"],
    "users": ["id", "organization_id", "email", "role", "metadata", "created_at"],
    "conversations": ["id", "user_id", "agent_id", "status", "metadata", "created_at"],
    "messages": ["id", "conversation_id", "role", "content", "metadata", "created_at"],
    "knowledge_chunks": ["id", "document_id", "content", "embedding", "metadata", "created_at"],
}


SECURITY_LAYERS = [
    "API Gateway: Rate limiting, IP blocking",
    "Application: Input validation, XSS protection",
    "Database: Row-level security, parameterized queries",
    "Encryption: TLS 1.3, field-level encryption",
    "Audit: Request logging, access logs",
]


K8S_DEPLOYMENT = {
    "namespace": "cuckoo-echo",
    "services": [
        {"name": "api-gateway", "replicas": 3, "cpu": "500m", "memory": "512Mi"},
        {"name": "chat-service", "replicas": 5, "cpu": "1000m", "memory": "1Gi"},
        {"name": "ai-gateway", "replicas": 3, "cpu": "2000m", "memory": "4Gi", "nvidia": "1"},
    ],
}


def get_system_architecture() -> dict[str, Any]:
    """Get system architecture overview."""
    return SYSTEM_COMPONENTS


def get_api_documentation() -> dict[str, Any]:
    """Get API endpoint documentation."""
    return API_ENDPOINTS


def get_database_schema() -> dict[str, list[str]]:
    """Get database schema."""
    return DATABASE_SCHEMA


def get_security_architecture() -> list[str]:
    """Get security architecture."""
    return SECURITY_LAYERS


def get_k8s_deployment() -> dict[str, Any]:
    """Get Kubernetes deployment config."""
    return K8S_DEPLOYMENT