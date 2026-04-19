"""Chat page routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from agent_tui.services.sessions import SessionStore
from agent_tui.web.routes.api import get_session_store

router = APIRouter()

# Setup templates
templates = Jinja2Templates(directory="src/agent_tui/web/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Any:
    """Redirect to chat or show empty state."""
    store = get_session_store()
    projects = await store.list_projects()
    
    if not projects:
        return templates.TemplateResponse(
            request,
            "chat.html",
            context={
                "projects": [],
                "chats": [],
                "current_project": None,
                "current_chat": None,
                "messages": [],
                "empty_state": True
            }
        )

    # Redirect to first project
    return templates.TemplateResponse(
        request,
        "chat.html",
        context={
            "projects": projects,
            "chats": [],
            "current_project": projects[0]["id"],
            "current_chat": None,
            "messages": [],
            "empty_state": False
        }
    )


@router.get("/chat/{chat_id}", response_class=HTMLResponse)
async def chat_page(chat_id: str, request: Request) -> Any:
    """Render chat page."""
    store = get_session_store()
    
    # Get all projects for sidebar
    projects = await store.list_projects()
    
    # Get current chat - try to get from store
    chat = None
    try:
        # Check all projects for this chat
        for project in projects:
            chats = await store.list_chats(project_id=project["id"])
            for c in chats:
                if c["id"] == chat_id:
                    chat = c
                    break
            if chat:
                break
    except Exception:
        pass
    
    if not chat:
        return templates.TemplateResponse(
            request,
            "chat.html",
            context={
                "projects": projects,
                "chats": [],
                "current_project": None,
                "current_chat": None,
                "messages": [],
                "error": "Chat not found"
            }
        )

    # Get chats for this project
    chats = await store.list_chats(project_id=chat.get("project_id"))

    # Messages would come from agent conversation history
    messages = []

    return templates.TemplateResponse(
        request,
        "chat.html",
        context={
            "projects": projects,
            "chats": chats,
            "current_project": chat.get("project_id"),
            "current_chat": chat_id,
            "messages": messages,
            "empty_state": False
        }
    )
