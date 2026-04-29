"""Integration tests for web interface."""

import asyncio
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from agent_tui.entrypoints.web import create_app
from agent_tui.web.routes.api import get_db_path, get_session_store


@pytest_asyncio.fixture
async def client():
    """Create test client with initialized database."""
    # Use a temporary database for testing
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_web_sessions.db"
        
        # Override the db_path function to use our test database
        original_db_path = get_db_path
        
        def mock_db_path():
            return db_path
        
        # Monkey patch the db_path function
        import agent_tui.web.routes.api
        agent_tui.web.routes.api.get_db_path = mock_db_path
        
        # Reset the global store to force re-initialization
        agent_tui.web.routes.api._session_store = None
        
        # Initialize the database
        store = get_session_store()
        await store.initialize()
        
        # Create the app and test client
        app = create_app()
        test_client = TestClient(app)
        
        yield test_client
        
        # Restore original db_path function
        agent_tui.web.routes.api.get_db_path = original_db_path
        agent_tui.web.routes.api._session_store = None


def test_index_page(client):
    """Test index page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AGENT-TUI WEB" in response.text


def test_static_css(client):
    """Test static CSS is served."""
    response = client.get("/static/css/output.css")
    assert response.status_code == 200
    assert len(response.text) > 0


def test_api_projects_endpoint(client):
    """Test API projects endpoint."""
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
