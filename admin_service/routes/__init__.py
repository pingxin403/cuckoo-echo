# Admin API routes
from admin_service.routes.analytics import router as analytics_router
from admin_service.routes.billing import router as billing_router
from admin_service.routes.config import router as config_router
from admin_service.routes.hitl import router as hitl_router
from admin_service.routes.knowledge import router as knowledge_router
from admin_service.routes.metrics import router as metrics_router
from admin_service.routes.plugins import router as plugins_router

__all__ = [
    "analytics_router",
    "billing_router",
    "knowledge_router",
    "hitl_router",
    "config_router",
    "metrics_router",
    "plugins_router",
]
