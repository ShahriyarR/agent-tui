# Web Interface Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web interface for agent-tui using FastAPI, Tailwind CSS, HTMX, and Alpine.js with neobrutalist design.

**Architecture:** Add FastAPI as a parallel entrypoint to the existing TUI. Reuse the existing `AgentProtocol` and services through a new `WebAdapter` that dispatches events to WebSocket connections instead of TUI widgets.

**Tech Stack:** FastAPI, Jinja2, Tailwind CSS, HTMX, Alpine.js, WebSocket, Server-Sent Events

**Reference Spec:** `docs/superpowers/specs/2026-04-19-web-interface-design.md`

---

## File Structure Overview

### New Files to Create
```
src/agent_tui/
├── entrypoints/
│   └── web.py                    # FastAPI entrypoint
├── services/
│   └── web_adapter.py            # Web event dispatcher
├── web/
│   ├── __init__.py
│   ├── state.py                  # Connection state management
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── chat.py               # Chat page + SSE
│   │   ├── api.py                # REST API endpoints
│   │   └── ws.py                 # WebSocket handler
│   ├── static/
│   │   ├── css/
│   │   │   └── app.css           # Tailwind source
│   │   └── js/
│   │       └── app.js            # Alpine.js components
│   ├── templates/
│   │   ├── base.html
│   │   ├── chat.html
│   │   ├── components/
│   │   │   ├── message.html
│   │   │   ├── tool_call.html
│   │   │   ├── approval_modal.html
│   │   │   ├── sidebar.html
│   │   │   └── project_modal.html
│   │   └── partials/
│   │       ├── message_stream.html
│   │       └── chat_list.html
│   └── tailwind.config.js
tests/web/
├── __init__.py
├── test_api.py
├── test_websocket.py
└── test_adapter.py
```

### Files to Modify
- `pyproject.toml` - add FastAPI dependencies
- `src/agent_tui/__init__.py` - add web CLI entrypoint

---

## Chunk 1: Dependencies and Basic Structure

### Task 1.1: Add FastAPI Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependencies**

Add to `[project.dependencies]`:
```toml
fastapi = ">=0.115.0"
uvicorn = {extras = ["standard"], version = ">=0.32.0"}
jinja2 = ">=3.1.0"
python-multipart = ">=0.0.17"
```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync
```

Expected: Dependencies installed successfully

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add FastAPI and related dependencies for web interface"
```

---

### Task 1.2: Create Web Package Structure

**Files:**
- Create: `src/agent_tui/web/__init__.py`
- Create: `src/agent_tui/web/state.py`
- Create: `src/agent_tui/web/routes/__init__.py`
- Create: `src/agent_tui/web/static/css/app.css`
- Create: `src/agent_tui/web/static/js/app.js`
- Create: `src/agent_tui/web/tailwind.config.js`

- [ ] **Step 1: Create `web/__init__.py`**

```python
"""Web interface for agent-tui."""

from agent_tui.web.state import ConnectionState, ConnectionManager

__all__ = ["ConnectionState", "ConnectionManager"]
```

- [ ] **Step 2: Create `web/state.py`**

```python
"""Per-connection state management for web interface."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from agent_tui.domain.protocol import AgentProtocol


@dataclass
class ConnectionState:
    """State for a single WebSocket connection."""
    
    websocket: WebSocket
    agent: AgentProtocol
    current_project_id: str | None = None
    current_thread_id: str | None = None
    pending_approvals: dict[str, asyncio.Event] = field(default_factory=dict)
    pending_answers: dict[str, asyncio.Event] = field(default_factory=dict)
    
    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON message to client."""
        await self.websocket.send_json(data)


class ConnectionManager:
    """Manages all active WebSocket connections."""
    
    def __init__(self) -> None:
        self._connections: dict[str, ConnectionState] = {}
    
    async def connect(self, client_id: str, state: ConnectionState) -> None:
        """Register a new connection."""
        self._connections[client_id] = state
    
    async def disconnect(self, client_id: str) -> None:
        """Remove a connection."""
        if client_id in self._connections:
            del self._connections[client_id]
    
    def get(self, client_id: str) -> ConnectionState | None:
        """Get connection state by client ID."""
        return self._connections.get(client_id)


# Global connection manager instance
connection_manager = ConnectionManager()
```

- [ ] **Step 3: Create `web/routes/__init__.py`**

```python
"""Web routes package."""

from agent_tui.web.routes.chat import router as chat_router
from agent_tui.web.routes.api import router as api_router
from agent_tui.web.routes.ws import router as ws_router

__all__ = ["chat_router", "api_router", "ws_router"]
```

- [ ] **Step 4: Create Tailwind config**

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        'nb-black': '#000000',
        'nb-white': '#FFFFFF',
        'nb-pink': '#FF006E',
        'nb-blue': '#3A86FF',
        'nb-green': '#06FFA5',
        'nb-yellow': '#FFBE0B',
        'nb-purple': '#8338EC',
        'nb-orange': '#FB5607',
        'nb-bg': '#F0F0F0',
        'nb-card': '#FFFFFF',
        'nb-dark': '#11121D',
      },
      boxShadow: {
        'nb': '4px 4px 0px 0px #000000',
        'nb-sm': '2px 2px 0px 0px #000000',
        'nb-lg': '6px 6px 0px 0px #000000',
        'nb-xl': '8px 8px 0px 0px #000000',
        'nb-pink': '4px 4px 0px 0px #FF006E',
        'nb-blue': '4px 4px 0px 0px #3A86FF',
      },
      borderWidth: {
        '3': '3px',
        '4': '4px',
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 5: Create CSS source file**

```css
/* static/css/app.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .nb-card {
    @apply border-3 border-nb-black shadow-nb bg-nb-card;
  }
  
  .nb-message-user {
    @apply border-3 border-nb-blue bg-blue-50 shadow-nb mb-4;
  }
  
  .nb-message-assistant {
    @apply border-3 border-nb-black bg-nb-card shadow-nb mb-4;
  }
  
  .nb-message-header {
    @apply border-b-3 border-nb-black bg-nb-yellow px-3 py-2 font-bold uppercase;
  }
  
  .nb-tool-card {
    @apply border-3 border-nb-pink shadow-nb-lg bg-pink-50 my-4;
  }
  
  .nb-tool-header {
    @apply bg-nb-pink text-white border-b-3 border-nb-black px-3 py-2 font-mono font-bold;
  }
  
  .nb-btn {
    @apply border-3 border-nb-black shadow-nb px-6 py-3 font-bold uppercase bg-nb-white 
           transition-all duration-100 hover:-translate-x-0.5 hover:-translate-y-0.5 
           hover:shadow-nb-sm active:translate-x-1 active:translate-y-1 active:shadow-none;
  }
  
  .nb-btn-primary {
    @apply nb-btn bg-nb-blue text-white;
  }
  
  .nb-btn-danger {
    @apply nb-btn bg-nb-orange text-white;
  }
  
  .nb-sidebar {
    @apply border-r-3 border-nb-black bg-nb-bg shadow-[-4px_0_0_0_#000000_inset];
  }
  
  .nb-sidebar-item {
    @apply border-b-2 border-nb-black px-4 py-4 font-bold hover:bg-nb-yellow;
  }
  
  .nb-sidebar-header {
    @apply border-b-3 border-nb-black bg-nb-black text-white px-4 py-3 font-bold uppercase;
  }
  
  .nb-modal-overlay {
    @apply fixed inset-0 bg-black/80 z-50 flex items-center justify-center;
  }
  
  .nb-modal {
    @apply border-4 border-nb-black shadow-nb-xl bg-nb-card max-w-lg w-full mx-4;
  }
  
  .nb-input {
    @apply border-3 border-nb-black shadow-nb px-4 py-3 w-full focus:outline-none 
           focus:shadow-nb-sm focus:-translate-x-0.5 focus:-translate-y-0.5;
  }
  
  .nb-status {
    @apply border-t-3 border-nb-black bg-nb-yellow px-4 py-2 font-bold uppercase text-sm;
  }
  
  .nb-token-counter {
    @apply border-3 border-nb-black bg-nb-purple text-white px-3 py-1 font-mono text-xs;
  }
}
```

- [ ] **Step 6: Create JS file**

```javascript
// static/js/app.js
// Alpine.js components for agent-tui web interface

document.addEventListener('alpine:init', () => {
  Alpine.data('chatApp', () => ({
    message: '',
    isStreaming: false,
    showProjectModal: false,
    currentProject: null,
    
    init() {
      this.$nextTick(() => {
        this.scrollToBottom();
      });
    },
    
    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },
    
    async sendMessage() {
      if (!this.message.trim() || this.isStreaming) return;
      
      this.isStreaming = true;
      const messageText = this.message;
      this.message = '';
      
      // Trigger HTMX request
      this.$refs.chatForm.dispatchEvent(new Event('submit'));
    },
    
    onStreamComplete() {
      this.isStreaming = false;
      this.$nextTick(() => this.scrollToBottom());
    }
  }));
  
  Alpine.data('approvalModal', () => ({
    show: false,
    toolName: '',
    toolArgs: {},
    toolId: '',
    
    open(toolName, toolArgs, toolId) {
      this.toolName = toolName;
      this.toolArgs = toolArgs;
      this.toolId = toolId;
      this.show = true;
    },
    
    close() {
      this.show = false;
    },
    
    approve() {
      this.$dispatch('tool-approved', { toolId: this.toolId, approved: true });
      this.close();
    },
    
    reject() {
      this.$dispatch('tool-approved', { toolId: this.toolId, approved: false });
      this.close();
    }
  }));
});
```

- [ ] **Step 7: Commit**

```bash
git add src/agent_tui/web/
git commit -m "feat(web): add basic package structure and tailwind config"
```

---

## Chunk 2: Database Schema for Projects

### Task 2.1: Extend Sessions Database

**Files:**
- Modify: `src/agent_tui/services/sessions.py`

- [ ] **Step 1: Write test for project schema**

Create `tests/web/test_projects.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/web/test_projects.py -v
```

Expected: FAIL - tables don't exist, methods don't exist

- [ ] **Step 3: Extend SessionStore with projects**

Modify `src/agent_tui/services/sessions.py`:

Add imports:
```python
from dataclasses import dataclass
from datetime import datetime
```

Add after existing table creation in `initialize()`:
```python
# Create projects table
await db.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        path TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Modify chat_sessions table to add project_id
await db.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL DEFAULT 'New Chat',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
""")

await db.execute("""
    CREATE INDEX IF NOT EXISTS idx_chats_project ON chat_sessions(project_id)
""")
```

Add new methods to SessionStore class:
```python
async def create_project(self, name: str, path: str) -> dict[str, Any]:
    """Create a new project."""
    import uuid
    
    project_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(
            """
            INSERT INTO projects (id, name, path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, name, path, now, now)
        )
        await db.commit()
    
    return {
        "id": project_id,
        "name": name,
        "path": path,
        "created_at": now,
        "updated_at": now,
    }

async def get_project(self, project_id: str) -> dict[str, Any] | None:
    """Get a project by ID."""
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def list_projects(self) -> list[dict[str, Any]]:
    """List all projects."""
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_project(self, project_id: str, name: str | None = None) -> dict[str, Any] | None:
    """Update a project."""
    async with aiosqlite.connect(self.db_path) as db:
        if name:
            await db.execute(
                "UPDATE projects SET name = ?, updated_at = ? WHERE id = ?",
                (name, datetime.now().isoformat(), project_id)
            )
            await db.commit()
    
    return await self.get_project(project_id)

async def delete_project(self, project_id: str) -> bool:
    """Delete a project and all its chats."""
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        return True

async def create_chat(self, title: str = "New Chat", project_id: str | None = None) -> dict[str, Any]:
    """Create a new chat session. Requires project_id."""
    if not project_id:
        raise ValueError("project_id is required for web interface")
    
    import uuid
    
    chat_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(
            """
            INSERT INTO chat_sessions (id, project_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, project_id, title, now, now)
        )
        await db.commit()
    
    return {
        "id": chat_id,
        "project_id": project_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }

async def list_chats(self, project_id: str | None = None) -> list[dict[str, Any]]:
    """List chat sessions, optionally filtered by project."""
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        
        if project_id:
            async with db.execute(
                "SELECT * FROM chat_sessions WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM chat_sessions ORDER BY updated_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/web/test_projects.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/web/test_projects.py src/agent_tui/services/sessions.py
git commit -m "feat(web): add project management to SessionStore"
```

---

## Chunk 3: Web Adapter

### Task 3.1: Create WebAdapter

**Files:**
- Create: `src/agent_tui/services/web_adapter.py`
- Create: `tests/web/test_adapter.py`

- [ ] **Step 1: Write test**

```python
"""Tests for WebAdapter."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from agent_tui.services.web_adapter import WebAdapter
from agent_tui.domain.protocol import AgentEvent, EventType


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = AsyncMock()
    return agent


@pytest.mark.asyncio
async def test_dispatch_message_chunk(mock_websocket, mock_agent):
    """Test dispatching MESSAGE_CHUNK event."""
    adapter = WebAdapter(mock_agent, mock_websocket)
    
    event = AgentEvent(type=EventType.MESSAGE_CHUNK, text="Hello")
    await adapter._dispatch(event)
    
    mock_websocket.send_json.assert_called_once_with({
        "type": "chunk",
        "text": "Hello"
    })


@pytest.mark.asyncio
async def test_dispatch_tool_call(mock_websocket, mock_agent):
    """Test dispatching TOOL_CALL event."""
    adapter = WebAdapter(mock_agent, mock_websocket)
    
    event = AgentEvent(
        type=EventType.TOOL_CALL,
        tool_id="tool_1",
        tool_name="bash",
        tool_args={"command": "echo hi"}
    )
    await adapter._dispatch(event)
    
    mock_websocket.send_json.assert_called_once_with({
        "type": "tool_call",
        "tool_id": "tool_1",
        "tool_name": "bash",
        "tool_args": {"command": "echo hi"}
    })


@pytest.mark.asyncio
async def test_dispatch_ask_user(mock_websocket, mock_agent):
    """Test dispatching ASK_USER event."""
    adapter = WebAdapter(mock_agent, mock_websocket)
    
    event = AgentEvent(
        type=EventType.ASK_USER,
        question="Which option?",
        metadata={"choices": [{"label": "A", "value": "a"}]}
    )
    await adapter._dispatch(event)
    
    mock_websocket.send_json.assert_called_once_with({
        "type": "ask_user",
        "question": "Which option?",
        "choices": [{"label": "A", "value": "a"}]
    })
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/web/test_adapter.py -v
```

Expected: FAIL - WebAdapter doesn't exist

- [ ] **Step 3: Implement WebAdapter**

Create `src/agent_tui/services/web_adapter.py`:

```python
"""Web adapter - dispatches AgentProtocol events to WebSocket."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

from agent_tui.domain.protocol import AgentEvent, AgentProtocol, EventType

logger = logging.getLogger(__name__)


class WebAdapter:
    """Dispatches AgentProtocol events to WebSocket client.
    
    Mirrors the existing AgentAdapter but sends events over WebSocket
    instead of calling TUI widget methods.
    """
    
    def __init__(self, agent: AgentProtocol, websocket: WebSocket) -> None:
        self.agent = agent
        self.websocket = websocket
    
    async def run_task(self, message: str, *, thread_id: str | None = None) -> None:
        """Stream events from agent and dispatch to WebSocket."""
        await self._send_status("thinking")
        
        try:
            async for event in self.agent.stream(message, thread_id=thread_id):
                await self._dispatch(event)
        except Exception:
            logger.exception("Agent stream error")
            await self._send_error("Agent stream encountered an unexpected error.")
        finally:
            await self._send_status("ready")
    
    async def _dispatch(self, event: AgentEvent) -> None:
        """Dispatch a single event to the WebSocket."""
        logger.debug("[WEB DISPATCH] Event type: %s", event.type)
        
        match event.type:
            case EventType.MESSAGE_CHUNK:
                await self.websocket.send_json({
                    "type": "chunk",
                    "text": event.text
                })
            
            case EventType.MESSAGE_END:
                await self.websocket.send_json({"type": "message_end"})
            
            case EventType.TOOL_CALL:
                await self.websocket.send_json({
                    "type": "tool_call",
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_args": event.tool_args
                })
            
            case EventType.TOOL_RESULT:
                await self.websocket.send_json({
                    "type": "tool_result",
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_output": event.tool_output
                })
            
            case EventType.ASK_USER:
                await self.websocket.send_json({
                    "type": "ask_user",
                    "question": event.question,
                    "metadata": event.metadata
                })
            
            case EventType.TOKEN_UPDATE:
                await self.websocket.send_json({
                    "type": "token_update",
                    "token_count": event.token_count,
                    "context_limit": event.context_limit
                })
            
            case EventType.STATUS_UPDATE:
                await self._send_status(event.status_text)
            
            case EventType.ERROR:
                await self._send_error(event.text)
            
            case EventType.PLAN_STEP:
                await self.websocket.send_json({
                    "type": "plan_step",
                    "text": event.plan_step_text,
                    "current": event.plan_current_step,
                    "total": event.plan_total_steps
                })
            
            case EventType.SUBAGENT_START:
                await self.websocket.send_json({
                    "type": "subagent_start",
                    "name": event.subagent_name
                })
            
            case EventType.SUBAGENT_END:
                await self.websocket.send_json({
                    "type": "subagent_end",
                    "name": event.subagent_name
                })
            
            case EventType.CONTEXT_SUMMARIZED:
                await self.websocket.send_json({
                    "type": "context_summarized",
                    "token_count": event.token_count
                })
            
            case EventType.INTERRUPT:
                await self.websocket.send_json({
                    "type": "interrupt",
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_args": event.tool_args
                })
            
            case _:
                logger.warning("Unknown event type: %s", event.type)
    
    async def _send_status(self, text: str) -> None:
        """Send status update."""
        await self.websocket.send_json({
            "type": "status",
            "text": text
        })
    
    async def _send_error(self, message: str) -> None:
        """Send error message."""
        await self.websocket.send_json({
            "type": "error",
            "message": message
        })
    
    async def approve_tool(self, tool_id: str, approved: bool) -> None:
        """Forward tool approval to agent."""
        await self.agent.approve_tool(tool_id, approved)
    
    async def answer_question(self, answer: str) -> None:
        """Forward user answer to agent."""
        await self.agent.answer_question(answer)
    
    async def cancel(self) -> None:
        """Cancel current execution."""
        await self.agent.cancel()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/web/test_adapter.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_tui/services/web_adapter.py tests/web/test_adapter.py
git commit -m "feat(web): add WebAdapter for dispatching events to WebSocket"
```

---

## Chunk 4: API Routes

### Task 4.1: Create REST API Routes

**Files:**
- Create: `src/agent_tui/web/routes/api.py`
- Create: `tests/web/test_api.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.fixture
def client():
    """Create test client."""
    from agent_tui.entrypoints.web import create_app
    app = create_app()
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/web/test_api.py -v
```

Expected: FAIL - routes don't exist

- [ ] **Step 3: Implement API routes**

Create `src/agent_tui/web/routes/api.py`:

```python
"""REST API routes for web interface."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_tui.services.sessions import SessionStore

router = APIRouter(prefix="/api")

# Global store instance (initialized on startup)
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get or create session store."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store


# Request/Response models
class CreateProjectRequest(BaseModel):
    name: str
    path: str


class UpdateProjectRequest(BaseModel):
    name: str


class CreateChatRequest(BaseModel):
    title: str = "New Chat"


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
    store = get_session_store()
    chat = await store.get_session(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str) -> dict[str, str]:
    """Delete a chat."""
    store = get_session_store()
    success = await store.delete_session(chat_id)
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
    # This will be populated when agent is available
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/web/test_api.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_tui/web/routes/api.py tests/web/test_api.py
git commit -m "feat(web): add REST API routes for projects and chats"
```

---

## Chunk 5: WebSocket Routes

### Task 5.1: Create WebSocket Handler

**Files:**
- Create: `src/agent_tui/web/routes/ws.py`

- [ ] **Step 1: Implement WebSocket routes**

Create `src/agent_tui/web/routes/ws.py`:

```python
"""WebSocket routes for real-time agent communication."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agent_tui.services.stub_agent import StubAgent
from agent_tui.services.web_adapter import WebAdapter
from agent_tui.web.state import ConnectionState, connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connections for agent communication."""
    await websocket.accept()
    
    client_id = str(uuid.uuid4())
    
    # Create agent instance (using stub for now)
    agent = StubAgent()
    
    # Create connection state
    state = ConnectionState(
        websocket=websocket,
        agent=agent
    )
    
    # Register connection
    await connection_manager.connect(client_id, state)
    
    # Create adapter
    adapter = WebAdapter(agent, websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            match msg_type:
                case "chat":
                    # Start streaming response
                    await adapter.run_task(
                        message.get("message", ""),
                        thread_id=message.get("thread_id")
                    )
                
                case "approve_tool":
                    await adapter.approve_tool(
                        message.get("tool_id", ""),
                        message.get("approved", False)
                    )
                
                case "answer":
                    await adapter.answer_question(message.get("answer", ""))
                
                case "cancel":
                    await adapter.cancel()
                
                case _:
                    logger.warning("Unknown message type: %s", msg_type)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}"
                    })
    
    except WebSocketDisconnect:
        logger.info("Client %s disconnected", client_id)
    except Exception:
        logger.exception("WebSocket error")
    finally:
        await connection_manager.disconnect(client_id)
```

- [ ] **Step 2: Commit**

```bash
git add src/agent_tui/web/routes/ws.py
git commit -m "feat(web): add WebSocket endpoint for real-time agent communication"
```

---

## Chunk 6: HTML Templates

### Task 6.1: Create Base Template

**Files:**
- Create: `src/agent_tui/web/templates/base.html`

- [ ] **Step 1: Create base template**

```html
<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Agent TUI Web{% endblock %}</title>
    
    <!-- Tailwind CSS -->
    <link rel="stylesheet" href="/static/css/output.css">
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@2.0.3"></script>
    <script src="https://unpkg.com/htmx.org/dist/ext/sse.js"></script>
    
    <!-- Alpine.js -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    
    <!-- App JS -->
    <script src="/static/js/app.js"></script>
    
    {% block head %}{% endblock %}
</head>
<body class="h-full bg-nb-bg font-sans" x-data="{% block alpine_data %}{}{% endblock %}">
    {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add src/agent_tui/web/templates/base.html
git commit -m "feat(web): add base HTML template"
```

---

### Task 6.2: Create Components

**Files:**
- Create: `src/agent_tui/web/templates/components/message.html`
- Create: `src/agent_tui/web/templates/components/tool_call.html`
- Create: `src/agent_tui/web/templates/components/approval_modal.html`
- Create: `src/agent_tui/web/templates/components/sidebar.html`
- Create: `src/agent_tui/web/templates/components/project_modal.html`

- [ ] **Step 1: Create message component**

```html
<!-- components/message.html -->
{% macro message(type, content, timestamp=None) -%}
<div class="{% if type == 'user' %}nb-message-user{% else %}nb-message-assistant{% endif %}">
    <div class="nb-message-header flex justify-between items-center">
        <span>{% if type == 'user' %}👤 You{% else %}🤖 Assistant{% endif %}</span>
        {% if timestamp %}
        <span class="text-xs opacity-70">{{ timestamp }}</span>
        {% endif %}
    </div>
    <div class="p-4 prose prose-sm max-w-none">
        {{ content|safe }}
    </div>
</div>
{%- endmacro %}
```

- [ ] **Step 2: Create tool call component**

```html
<!-- components/tool_call.html -->
{% macro tool_call(tool_name, tool_id, tool_args) -%}
<div class="nb-tool-card" id="tool-{{ tool_id }}">
    <div class="nb-tool-header flex justify-between items-center">
        <span>🔧 {{ tool_name }}</span>
        <code class="text-xs bg-black/20 px-2 py-1">{{ tool_id }}</code>
    </div>
    <div class="p-4">
        <pre class="bg-black/5 p-3 font-mono text-sm overflow-x-auto"><code>{{ tool_args|tojson(indent=2) }}</code></pre>
        <div class="mt-4 flex gap-3" id="tool-actions-{{ tool_id }}">
            <button class="nb-btn-primary" onclick="approveTool('{{ tool_id }}', true)">Approve</button>
            <button class="nb-btn" onclick="approveTool('{{ tool_id }}', false)">Reject</button>
        </div>
    </div>
</div>
{%- endmacro %}
```

- [ ] **Step 3: Create approval modal**

```html
<!-- components/approval_modal.html -->
<div x-data="approvalModal" 
     x-show="show" 
     x-cloak
     class="nb-modal-overlay"
     @keydown.escape.window="close()">
    <div class="nb-modal" @click.away="close()">
        <div class="border-b-3 border-nb-black bg-nb-yellow px-4 py-3 flex justify-between items-center">
            <span class="font-bold uppercase">🔧 Tool Approval</span>
            <button @click="close()" class="font-bold text-xl">&times;</button>
        </div>
        <div class="p-6">
            <p class="mb-4">The agent wants to run: <code class="bg-gray-100 px-2 py-1 font-mono" x-text="toolName"></code></p>
            <pre class="bg-black/5 p-3 font-mono text-sm overflow-x-auto mb-6"><code x-text="JSON.stringify(toolArgs, null, 2)"></code></pre>
            <div class="flex gap-3 justify-end">
                <button @click="reject()" class="nb-btn">Reject</button>
                <button @click="approve()" class="nb-btn-primary">Approve</button>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 4: Create sidebar component**

```html
<!-- components/sidebar.html -->
<aside class="nb-sidebar w-64 h-screen flex flex-col">
    <div class="nb-sidebar-header">Projects</div>
    <nav class="flex-1 overflow-y-auto">
        {% for project in projects %}
        <div class="border-b-2 border-nb-black">
            <a href="/chat?project={{ project.id }}" 
               class="nb-sidebar-item block {% if current_project == project.id %}bg-nb-yellow{% endif %}">
                {{ project.name }}
            </a>
        </div>
        {% endfor %}
    </nav>
    <div class="p-4 border-t-3 border-nb-black">
        <button @click="showProjectModal = true" class="nb-btn-primary w-full">+ Add Project</button>
    </div>
    
    <div class="nb-sidebar-header">Chats</div>
    <nav class="flex-1 overflow-y-auto">
        {% for chat in chats %}
        <a href="/chat/{{ chat.id }}" 
           class="nb-sidebar-item block pl-8 text-sm {% if current_chat == chat.id %}bg-nb-yellow{% endif %}">
            {{ chat.title }}
        </a>
        {% endfor %}
    </nav>
    {% if current_project %}
    <div class="p-4 border-t-3 border-nb-black">
        <button class="nb-btn w-full" hx-post="/api/projects/{{ current_project }}/chats" hx-swap="none">+ New Chat</button>
    </div>
    {% endif %}
</aside>
```

- [ ] **Step 5: Create project modal**

```html
<!-- components/project_modal.html -->
<div x-show="showProjectModal" 
     x-cloak
     class="nb-modal-overlay"
     @keydown.escape.window="showProjectModal = false">
    <div class="nb-modal" @click.away="showProjectModal = false">
        <div class="border-b-3 border-nb-black bg-nb-yellow px-4 py-3 flex justify-between items-center">
            <span class="font-bold uppercase">Add New Project</span>
            <button @click="showProjectModal = false" class="font-bold text-xl">&times;</button>
        </div>
        <form hx-post="/api/projects" hx-swap="none" @htmx:after-request="showProjectModal = false; window.location.reload()" class="p-6">
            <div class="mb-4">
                <label class="block font-bold mb-2">Project Path:</label>
                <input type="text" name="path" class="nb-input" placeholder="/home/user/my-project" required>
            </div>
            <div class="mb-6">
                <label class="block font-bold mb-2">Display Name:</label>
                <input type="text" name="name" class="nb-input" placeholder="My Project" required>
            </div>
            <div class="flex gap-3 justify-end">
                <button type="button" @click="showProjectModal = false" class="nb-btn">Cancel</button>
                <button type="submit" class="nb-btn-primary">Add Project</button>
            </div>
        </form>
    </div>
</div>
```

- [ ] **Step 6: Commit**

```bash
git add src/agent_tui/web/templates/components/
git commit -m "feat(web): add HTML component templates"
```

---

## Chunk 7: Chat Page

### Task 7.1: Create Chat Routes and Template

**Files:**
- Create: `src/agent_tui/web/routes/chat.py`
- Create: `src/agent_tui/web/templates/chat.html`

- [ ] **Step 1: Implement chat routes**

Create `src/agent_tui/web/routes/chat.py`:

```python
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
            "chat.html",
            {
                "request": request,
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
        "chat.html",
        {
            "request": request,
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
    
    # Get current chat
    chat = await store.get_session(chat_id)
    if not chat:
        return templates.TemplateResponse(
            "chat.html",
            {
                "request": request,
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
    
    # Get messages for this chat
    messages = await store.get_messages(chat_id)
    
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "projects": projects,
            "chats": chats,
            "current_project": chat.get("project_id"),
            "current_chat": chat_id,
            "messages": messages,
            "empty_state": False
        }
    )
```

- [ ] **Step 2: Create chat template**

Create `src/agent_tui/web/templates/chat.html`:

```html
{% extends "base.html" %}

{% block title %}Chat - Agent TUI Web{% endblock %}

{% block alpine_data %}chatApp{% endblock %}

{% block content %}
<div class="h-full flex flex-col">
    <!-- Header -->
    <header class="border-b-3 border-nb-black bg-nb-yellow px-4 py-3 flex justify-between items-center">
        <div class="flex items-center gap-4">
            <span class="font-bold text-xl">▓▓▓ AGENT-TUI WEB ▓▓▓</span>
            {% if current_project %}
            <select class="nb-input py-1 text-sm">
                {% for project in projects %}
                <option value="{{ project.id }}" {% if project.id == current_project %}selected{% endif %}>
                    {{ project.name }}
                </option>
                {% endfor %}
            </select>
            {% endif %}
        </div>
        <div class="flex gap-3">
            <button @click="showProjectModal = true" class="nb-btn text-sm py-2">+ Add Project</button>
            <button class="nb-btn text-sm py-2">⚙️</button>
        </div>
    </header>
    
    {% if empty_state %}
    <!-- Empty State -->
    <div class="flex-1 flex items-center justify-center">
        <div class="nb-card p-8 text-center max-w-md">
            <div class="text-6xl mb-4">📁</div>
            <h2 class="text-xl font-bold mb-2">No projects yet</h2>
            <p class="mb-6 text-gray-600">Add your first project to start chatting with AI</p>
            <button @click="showProjectModal = true" class="nb-btn-primary">+ Add Project</button>
        </div>
    </div>
    {% else %}
    <!-- Main Layout -->
    <div class="flex-1 flex overflow-hidden">
        <!-- Sidebar -->
        {% include "components/sidebar.html" %}
        
        <!-- Chat Area -->
        <main class="flex-1 flex flex-col bg-nb-bg">
            <!-- Messages -->
            <div x-ref="messagesContainer" class="flex-1 overflow-y-auto p-4">
                {% if current_chat %}
                    {% for msg in messages %}
                        {% from "components/message.html" import message %}
                        {{ message(msg.type, msg.content, msg.timestamp) }}
                    {% endfor %}
                {% else %}
                    <div class="flex items-center justify-center h-full text-gray-500">
                        Select a chat or create a new one
                    </div>
                {% endif %}
                
                <!-- Streaming content goes here -->
                <div id="streaming-content"></div>
            </div>
            
            <!-- Input Area -->
            {% if current_chat %}
            <div class="border-t-3 border-nb-black bg-nb-bg p-4">
                <form x-ref="chatForm" 
                      hx-post="/api/chat/{{ current_chat }}/stream"
                      hx-swap="none"
                      @submit.prevent="sendMessage()"
                      class="flex gap-3">
                    <input type="text" 
                           x-model="message"
                           class="nb-input flex-1"
                           placeholder="Type your message..."
                           :disabled="isStreaming"
                           @keydown.enter.prevent="sendMessage()">
                    <button type="submit" 
                            class="nb-btn-primary"
                            :disabled="isStreaming || !message.trim()">
                        <span x-show="!isStreaming">Send</span>
                        <span x-show="isStreaming">...</span>
                    </button>
                </form>
            </div>
            {% endif %}
        </main>
    </div>
    {% endif %}
    
    <!-- Modals -->
    {% include "components/project_modal.html" %}
    {% include "components/approval_modal.html" %}
</div>

<script>
// WebSocket connection for real-time updates
let ws = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onclose = function() {
        console.log('WebSocket closed, reconnecting...');
        setTimeout(connectWebSocket, 1000);
    };
}

function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'chunk':
            appendChunk(data.text);
            break;
        case 'message_end':
            Alpine.store('chatApp').onStreamComplete();
            break;
        case 'tool_call':
            showToolApproval(data);
            break;
        case 'status':
            updateStatus(data.text);
            break;
        case 'error':
            showError(data.message);
            break;
    }
}

function appendChunk(text) {
    const container = document.getElementById('streaming-content');
    container.innerHTML += text;
}

function showToolApproval(data) {
    // Dispatch to Alpine component
    window.dispatchEvent(new CustomEvent('tool-call-received', { detail: data }));
}

function approveTool(toolId, approved) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'approve_tool',
            tool_id: toolId,
            approved: approved
        }));
    }
}

function updateStatus(text) {
    // Update status indicator
}

function showError(message) {
    alert('Error: ' + message);
}

// Connect on load
connectWebSocket();
</script>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add src/agent_tui/web/routes/chat.py src/agent_tui/web/templates/chat.html
git commit -m "feat(web): add chat page routes and template"
```

---

## Chunk 8: FastAPI Entrypoint

### Task 8.1: Create Web Entrypoint

**Files:**
- Create: `src/agent_tui/entrypoints/web.py`
- Modify: `src/agent_tui/__init__.py`

- [ ] **Step 1: Create web entrypoint**

Create `src/agent_tui/entrypoints/web.py`:

```python
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
        logger.info("Starting Agent TUI Web server")
        # Initialize session store
        from agent_tui.web.routes.api import get_session_store
        store = get_session_store()
        await store.initialize()
    
    return app


def main():
    """Entry point for web server."""
    import uvicorn
    
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
```

- [ ] **Step 2: Add CLI entrypoint**

Modify `src/agent_tui/__init__.py`:

Add to imports:
```python
import argparse
import sys
```

Modify `cli_main()`:
```python
def cli_main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Agent TUI")
    parser.add_argument(
        "--agent",
        choices=["stub", "deepagents"],
        default="stub",
        help="Agent backend to use",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start web interface instead of TUI",
    )
    
    args = parser.parse_args()
    
    # Start web interface if requested
    if args.web:
        from agent_tui.entrypoints.web import main as web_main
        web_main()
        return 0
    
    # Otherwise start TUI (existing code)
    load_dotenv()
    
    if args.agent == "deepagents":
        ...
    
    # ... rest of existing TUI code
```

- [ ] **Step 3: Test entrypoint**

```bash
uv run python -c "from agent_tui.entrypoints.web import create_app; app = create_app(); print('App created successfully')"
```

Expected: "App created successfully"

- [ ] **Step 4: Commit**

```bash
git add src/agent_tui/entrypoints/web.py src/agent_tui/__init__.py
git commit -m "feat(web): add FastAPI entrypoint and CLI integration"
```

---

## Chunk 9: Build Process

### Task 9.1: Setup Tailwind Build

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add npm scripts to pyproject.toml**

Add to `[tool.hatch.envs.default]` or as scripts:
```toml
[project.scripts]
agent-tui = "agent_tui:cli_main"

[tool.hatch.envs.default.scripts]
tailwind = "npx tailwindcss -i src/agent_tui/web/static/css/app.css -o src/agent_tui/web/static/css/output.css --watch"
tailwind-build = "npx tailwindcss -i src/agent_tui/web/static/css/app.css -o src/agent_tui/web/static/css/output.css --minify"
```

- [ ] **Step 2: Create initial CSS build**

```bash
cd /home/shako/REPOS/Indie-Hacking/agent-tui
npx tailwindcss -i src/agent_tui/web/static/css/app.css -o src/agent_tui/web/static/css/output.css
```

Expected: output.css created

- [ ] **Step 3: Commit**

```bash
git add src/agent_tui/web/static/css/output.css pyproject.toml
git commit -m "feat(web): add Tailwind build setup and initial CSS"
```

---

## Chunk 10: Integration Testing

### Task 10.1: End-to-End Test

**Files:**
- Create: `tests/web/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
"""Integration tests for web interface."""

import pytest
from fastapi.testclient import TestClient

from agent_tui.entrypoints.web import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_index_page(client):
    """Test index page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AGENT-TUI WEB" in response.text


def test_static_css(client):
    """Test static CSS is served."""
    response = client.get("/static/css/output.css")
    assert response.status_code == 200
    assert "tailwind" in response.text.lower() or "nb-" in response.text


def test_api_projects_endpoint(client):
    """Test API projects endpoint."""
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 2: Run integration tests**

```bash
uv run pytest tests/web/test_integration.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/web/test_integration.py
git commit -m "test(web): add integration tests"
```

---

## Chunk 11: Documentation

### Task 11.1: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add web interface section to README**

Add after Quick Start section:

```markdown
## Web Interface

### Start Web Server

```bash
# Start the web interface
uv run agent-tui --web
```

Then open http://localhost:8000 in your browser.

### Web Interface Features

- **Projects**: Organize chats by project (working directory)
- **Real-time Chat**: WebSocket-based streaming responses
- **Tool Approval**: Interactive approval/rejection of tool calls
- **Neobrutalist Design**: Bold, high-contrast UI

### Development

Build Tailwind CSS:
```bash
# Watch mode
npx tailwindcss -i src/agent_tui/web/static/css/app.css -o src/agent_tui/web/static/css/output.css --watch

# Production build
npx tailwindcss -i src/agent_tui/web/static/css/app.css -o src/agent_tui/web/static/css/output.css --minify
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add web interface documentation"
```

---

## Final Verification

### Run All Tests

```bash
uv run pytest tests/web/ -v
```

Expected: All tests PASS

### Manual Test

```bash
# Terminal 1: Start server
uv run agent-tui --web

# Terminal 2: Verify
# Open http://localhost:8000
# Should see empty state with "Add Project" button
```

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-19-web-interface-implementation.md`. Ready to execute?**

To execute, use: **superpowers:subagent-driven-development**
