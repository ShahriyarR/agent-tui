"""Tests for project management in web interface."""

import pytest
from pathlib import Path

from agent_tui.services.sessions import SessionStore


@pytest.fixture
async def session_store(tmp_path):
    """Create a temporary session store."""
    db_path = tmp_path / "test.db"
    store = SessionStore(db_path=str(db_path))
    await store.initialize()
    return store


@pytest.mark.asyncio
async def test_create_project(session_store):
    """Test creating a project."""
    project = await session_store.create_project(
        name="Test Project",
        path="/home/user/test"
    )
    assert project["name"] == "Test Project"
    assert project["path"] == "/home/user/test"
    assert "id" in project


@pytest.mark.asyncio
async def test_get_project(session_store):
    """Test retrieving a project."""
    created = await session_store.create_project(
        name="Test Project",
        path="/home/user/test"
    )
    
    retrieved = await session_store.get_project(created["id"])
    assert retrieved["name"] == "Test Project"
    assert retrieved["path"] == "/home/user/test"


@pytest.mark.asyncio
async def test_list_projects(session_store):
    """Test listing all projects."""
    await session_store.create_project(name="Project A", path="/path/a")
    await session_store.create_project(name="Project B", path="/path/b")
    
    projects = await session_store.list_projects()
    assert len(projects) == 2
    assert {p["name"] for p in projects} == {"Project A", "Project B"}


@pytest.mark.asyncio
async def test_create_chat_requires_project(session_store):
    """Test that creating a chat requires a project."""
    with pytest.raises(ValueError, match="project_id is required"):
        await session_store.create_chat(title="Test Chat")


@pytest.mark.asyncio
async def test_create_chat_with_project(session_store):
    """Test creating a chat within a project."""
    project = await session_store.create_project(
        name="Test Project",
        path="/home/user/test"
    )
    
    chat = await session_store.create_chat(
        title="Test Chat",
        project_id=project["id"]
    )
    assert chat["title"] == "Test Chat"
    assert chat["project_id"] == project["id"]


@pytest.mark.asyncio
async def test_list_chats_for_project(session_store):
    """Test listing chats filtered by project."""
    project1 = await session_store.create_project(name="P1", path="/p1")
    project2 = await session_store.create_project(name="P2", path="/p2")
    
    await session_store.create_chat(title="Chat 1", project_id=project1["id"])
    await session_store.create_chat(title="Chat 2", project_id=project1["id"])
    await session_store.create_chat(title="Chat 3", project_id=project2["id"])
    
    p1_chats = await session_store.list_chats(project_id=project1["id"])
    assert len(p1_chats) == 2
    assert {c["title"] for c in p1_chats} == {"Chat 1", "Chat 2"}
