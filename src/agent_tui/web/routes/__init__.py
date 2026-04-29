"""Web routes package."""

from agent_tui.web.routes.chat import router as chat_router
from agent_tui.web.routes.api import router as api_router
from agent_tui.web.routes.ws import router as ws_router

__all__ = ["chat_router", "api_router", "ws_router"]
