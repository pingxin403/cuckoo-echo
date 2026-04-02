# Admin backend service
from admin_service.routes import knowledge_router, hitl_router, config_router, metrics_router

__all__ = ["knowledge_router", "hitl_router", "config_router", "metrics_router"]
