"""FastAPI entrypoint for agent-tui web interface."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from agent_tui.web.routes.api import router as api_router
from agent_tui.web.routes.chat import router as chat_router
from agent_tui.web.routes.ws import router as ws_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Agent TUI Web",
        description="Web interface for agent-tui",
        version="0.1.0"
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="src/agent_tui/web/static"), name="static")
    
    # Include routers
    app.include_router(api_router)
    app.include_router(chat_router)
    app.include_router(ws_router)
    
    @app.on_event("startup")
    async def startup():
        """Initialize services on startup."""
        import os
        agent_type = os.environ.get('AGENT_TUI_WEB_AGENT', 'stub')
        logger.info(f"Starting Agent TUI Web server with {agent_type} agent")
        # Initialize session store
        from agent_tui.web.routes.api import get_session_store
        store = get_session_store()
        await store.initialize()
        logger.info("Session store initialized")
    
    return app


def main():
    """Entry point for web server."""
    import uvicorn
    from pathlib import Path
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    uvicorn.run(
        "agent_tui.entrypoints.web:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
