# Chat service API routes

from chat_service.routes.chat import router as chat_router
from chat_service.routes.ws_chat import router as ws_chat_router

__all__ = ["chat_router", "ws_chat_router"]
