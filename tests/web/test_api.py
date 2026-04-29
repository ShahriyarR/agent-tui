"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.fixture
def client():
    """Create test client."""
    from fastapi import FastAPI
    from agent_tui.web.routes.api import router as api_router
    
    app = FastAPI()
    app.include_router(api_router)
    return TestClient(app)


def test_list_projects_empty(client):
    """Test listing projects when none exist."""
    with patch("agent_tui.web.routes.api.get_session_store") as mock_store:
        mock_store.return_value.list_projects = AsyncMock(return_value=[])
        
        response = client.get("/api/projects")
        assert response.status_code == 200
        assert response.json() == []


def test_create_project(client):
    """Test creating a project."""
    with patch("agent_tui.web.routes.api.get_session_store") as mock_store:
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            mock_store.return_value.create_project = AsyncMock(return_value={
                "id": "proj_123",
                "name": "Test Project",
                "path": "/home/user/test"
            })
            
            response = client.post("/api/projects", json={
                "name": "Test Project",
                "path": "/home/user/test"
            })
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Test Project"


def test_list_chats_for_project(client):
    """Test listing chats for a project."""
    with patch("agent_tui.web.routes.api.get_session_store") as mock_store:
        mock_store.return_value.list_chats = AsyncMock(return_value=[
            {"id": "chat_1", "title": "Chat 1"},
            {"id": "chat_2", "title": "Chat 2"}
        ])
        
        response = client.get("/api/projects/proj_123/chats")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
