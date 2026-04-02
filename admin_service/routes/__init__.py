# Admin API routes
from admin_service.routes.knowledge import router as knowledge_router
from admin_service.routes.hitl import router as hitl_router

__all__ = ["knowledge_router", "hitl_router"]
