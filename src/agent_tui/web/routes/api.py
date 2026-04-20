"""REST API routes for web interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_tui.services.sessions import SessionStore

router = APIRouter(prefix="/api")

# Global store instance (initialized on startup)
_session_store: SessionStore | None = None


def get_db_path() -> Path:
    """Get path to web sessions database."""
    db_dir = Path.home() / ".agent-tui"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "web_sessions.db"


def get_session_store() -> SessionStore:
    """Get or create session store."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore(db_path=get_db_path())
    return _session_store


# Request/Response models
class CreateProjectRequest(BaseModel):
    name: str
    path: str


class UpdateProjectRequest(BaseModel):
    name: str


class CreateChatRequest(BaseModel):
    title: str = "New Chat"


class CreateMessageRequest(BaseModel):
    role: str
    content: str


# Project endpoints
@router.get("/projects")
async def list_projects() -> list[dict[str, Any]]:
    """List all projects."""
    store = get_session_store()
    return await store.list_projects()


@router.post("/projects", status_code=201)
async def create_project(request: CreateProjectRequest) -> dict[str, Any]:
    """Create a new project."""
    store = get_session_store()
    
    # Validate path exists
    from pathlib import Path
    if not Path(request.path).exists():
        raise HTTPException(status_code=400, detail="Path does not exist")
    
    return await store.create_project(name=request.name, path=request.path)


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    """Get a project by ID."""
    store = get_session_store()
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest) -> dict[str, Any]:
    """Update a project."""
    store = get_session_store()
    project = await store.update_project(project_id, name=request.name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str) -> dict[str, str]:
    """Delete a project."""
    store = get_session_store()
    success = await store.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted"}


# Chat endpoints (project-scoped)
@router.get("/projects/{project_id}/chats")
async def list_chats(project_id: str) -> list[dict[str, Any]]:
    """List all chats for a project."""
    store = get_session_store()
    return await store.list_chats(project_id=project_id)


@router.post("/projects/{project_id}/chats", status_code=201)
async def create_chat(project_id: str, request: CreateChatRequest) -> dict[str, Any]:
    """Create a new chat in a project."""
    store = get_session_store()
    
    # Verify project exists
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return await store.create_chat(title=request.title, project_id=project_id)


@router.get("/chats/{chat_id}")
async def get_chat(chat_id: str) -> dict[str, Any]:
    """Get a chat by ID."""
    # TODO: Implement get_chat method in SessionStore
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/chats/{chat_id}")
async def update_chat(chat_id: str, request: CreateChatRequest) -> dict[str, Any]:
    """Update a chat's title."""
    store = get_session_store()
    chat = await store.update_chat(chat_id, title=request.title)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str) -> dict[str, str]:
    """Delete a chat."""
    store = get_session_store()
    success = await store.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "deleted"}


# Agent info endpoints
@router.get("/models")
async def list_models() -> list[dict[str, Any]]:
    """List available models (requires agent)."""
    # This will be populated when agent is available
    return []


@router.get("/skills")
async def list_skills() -> list[dict[str, Any]]:
    """List available skills (requires agent)."""
    # Return stub agent skills for now
    return [
        {"name": "search", "description": "Search the web for information", "command": "/search"},
        {"name": "summarize", "description": "Summarize a document or URL", "command": "/summarize"},
        {"name": "analyze", "description": "Analyze code or data", "command": "/analyze"},
        {"name": "git", "description": "Git operations (status, diff, commit)", "command": "/git"},
        {"name": "test", "description": "Run tests for the project", "command": "/test"},
        {"name": "lint", "description": "Run linter on the codebase", "command": "/lint"},
    ]


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get server status including active agent type."""
    import os
    agent_type = os.environ.get('AGENT_TUI_WEB_AGENT', 'stub')
    return {
        "status": "ok",
        "agent_type": agent_type,
        "version": "0.1.0"
    }


# Message endpoints
@router.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: str) -> list[dict[str, Any]]:
    """Get all messages for a chat."""
    store = get_session_store()
    return await store.get_messages(chat_id)


@router.post("/chats/{chat_id}/messages", status_code=201)
async def create_message(chat_id: str, request: CreateMessageRequest) -> dict[str, Any]:
    """Add a message to a chat."""
    store = get_session_store()
    return await store.add_message(
        chat_id=chat_id,
        role=request.role,
        content=request.content
    )
