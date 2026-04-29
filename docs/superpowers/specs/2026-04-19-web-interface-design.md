# Web Interface Design for agent-tui

**Date**: 2026-04-19  
**Status**: Approved  
**Author**: AI Assistant + User

---

## 1. Overview

### 1.1 Goal
Create a web-based interface for the agent-tui coding AI agent as an alternative entrypoint to the existing TUI. The web interface will eventually become the primary interface as TUI is deprecated.

### 1.2 Feasibility Assessment
**Score: 9/10** - Highly feasible due to:
- Clean `AgentProtocol` abstraction that can be reused without modification
- Event-driven architecture (`AgentEvent` / `EventType`) maps perfectly to web streaming
- Existing `AgentAdapter` pattern shows how to dispatch events to a UI layer
- All business logic (sessions, file operations, tool handling) is decoupled from TUI

### 1.3 Constraints
- **Stack**: FastAPI, Jinja2 templates, Tailwind CSS, HTMX, Alpine.js
- **Style**: Neobrutalist design (hard shadows, thick borders, bold colors, no rounding)
- **CSS**: No inline styles - only shared Tailwind utility classes
- **Scope**: Full feature parity with TUI
- **Architecture**: Web-first, every chat must belong to a project

---

## 2. Architecture

### 2.1 Module Structure

```
src/agent_tui/
├── entrypoints/
│   ├── app.py              # TUI entrypoint (existing)
│   └── web.py              # FastAPI entrypoint (new)
├── services/
│   ├── adapter.py          # TUI adapter (existing)
│   ├── web_adapter.py      # Web adapter (new)
│   ├── sessions.py         # Shared (existing)
│   └── stub_agent.py       # Shared (existing)
├── web/                    # NEW: Web-specific code
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── chat.py         # Chat page (GET /, SSE streaming)
│   │   ├── api.py          # REST API (projects, threads, models, skills)
│   │   └── ws.py           # WebSocket handler
│   ├── static/
│   │   ├── css/
│   │   │   ├── app.css     # Tailwind source
│   │   │   └── output.css  # Compiled output (gitignored)
│   │   └── js/
│   │       └── app.js      # Alpine.js components
│   ├── templates/
│   │   ├── base.html       # Layout with HTMX + Alpine
│   │   ├── chat.html       # Main chat interface
│   │   ├── components/     # Reusable UI pieces
│   │   │   ├── message.html
│   │   │   ├── tool_call.html
│   │   │   └── approval_modal.html
│   │   └── partials/       # HTMX-swap targets
│   │       ├── message_stream.html
│   │       └── tool_result.html
│   ├── state.py            # Per-connection state management
│   └── tailwind.config.js  # Tailwind configuration
└── domain/
    └── protocol.py         # Shared AgentProtocol
```

### 2.2 Communication Protocol

**Hybrid WebSocket + SSE Approach**:

| Transport | Direction | Use Case |
|-----------|-----------|----------|
| WebSocket | Bidirectional | Control messages, tool approvals, answers, status updates |
| SSE | Server→Client | Message streaming (better reconnection handling) |

**WebSocket Message Format**:
```json
// Client → Server
{"type": "chat", "message": "hello", "thread_id": "abc123", "project_id": "proj_1"}
{"type": "approve_tool", "tool_id": "tool_1", "approved": true}
{"type": "answer", "answer": "Option A"}

// Server → Client  
{"type": "tool_call", "tool_id": "tool_1", "tool_name": "bash", "args": {...}}
{"type": "tool_result", "tool_id": "tool_1", "output": "..."}
{"type": "ask_user", "question": "Which option?", "choices": [...]}
{"type": "status", "text": "thinking"}
{"type": "token_update", "count": 1234, "limit": 128000}
{"type": "error", "message": "Connection failed"}
```

**SSE Stream Format**:
```
data: {"type": "chunk", "text": "Hello"}

data: {"type": "chunk", "text": " world"}

data: {"type": "end"}
```

### 2.3 Event Mapping

| AgentEvent Type | Web Transport | UI Action |
|-----------------|---------------|-----------|
| `MESSAGE_CHUNK` | SSE | Append text to message container |
| `MESSAGE_END` | WebSocket | Finalize message, enable input |
| `TOOL_CALL` | WebSocket | Show approval modal |
| `TOOL_RESULT` | WebSocket | Display result in collapsible card |
| `ASK_USER` | WebSocket | Show question prompt/modal |
| `TOKEN_UPDATE` | WebSocket | Update token counter display |
| `STATUS_UPDATE` | WebSocket | Update status bar text |
| `ERROR` | WebSocket | Show error toast/notification |

---

## 3. UI Design (Neobrutalist)

### 3.1 Visual Identity

- **Borders**: 3px solid black (no exceptions)
- **Shadows**: Hard offset shadows (4px 4px 0px black) — no blur
- **Corners**: 0px border-radius (no rounding)
- **Colors**: Bold clashing palette
- **Typography**: Monospace for code, bold sans-serif for UI

### 3.2 Color Palette

```css
:root {
  --nb-black: #000000;
  --nb-white: #FFFFFF;
  --nb-pink: #FF006E;      /* Tool calls, accents */
  --nb-blue: #3A86FF;      /* Primary, links */
  --nb-green: #06FFA5;     /* Success, additions */
  --nb-yellow: #FFBE0B;    /* Warnings, highlights */
  --nb-purple: #8338EC;    /* Secondary, skills */
  --nb-orange: #FB5607;    /* Errors, destructive */
  --nb-bg: #F0F0F0;        /* Main background */
  --nb-card: #FFFFFF;      /* Card backgrounds */
  --nb-dark: #11121D;      /* Dark mode background */
}
```

### 3.3 Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
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
}
```

### 3.4 CSS Components (app.css)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  /* Base Card */
  .nb-card {
    @apply border-3 border-nb-black shadow-nb bg-nb-card;
  }
  
  /* Messages */
  .nb-message-user {
    @apply border-3 border-nb-blue bg-blue-50 shadow-nb mb-4;
  }
  
  .nb-message-assistant {
    @apply border-3 border-nb-black bg-nb-card shadow-nb mb-4;
  }
  
  .nb-message-header {
    @apply border-b-3 border-nb-black bg-nb-yellow px-3 py-2 font-bold uppercase;
  }
  
  /* Tool Call Card */
  .nb-tool-card {
    @apply border-3 border-nb-pink shadow-nb-lg bg-pink-50 my-4;
  }
  
  .nb-tool-header {
    @apply bg-nb-pink text-white border-b-3 border-nb-black px-3 py-2 font-mono font-bold;
  }
  
  /* Buttons */
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
  
  /* Sidebar */
  .nb-sidebar {
    @apply border-r-3 border-nb-black bg-nb-bg shadow-[-4px_0_0_0_#000000_inset];
  }
  
  .nb-sidebar-item {
    @apply border-b-2 border-nb-black px-4 py-4 font-bold hover:bg-nb-yellow;
  }
  
  .nb-sidebar-header {
    @apply border-b-3 border-nb-black bg-nb-black text-white px-4 py-3 font-bold uppercase;
  }
  
  /* Modal */
  .nb-modal-overlay {
    @apply fixed inset-0 bg-black/80 z-50 flex items-center justify-center;
  }
  
  .nb-modal {
    @apply border-4 border-nb-black shadow-nb-xl bg-nb-card max-w-lg w-full mx-4;
  }
  
  /* Input */
  .nb-input {
    @apply border-3 border-nb-black shadow-nb px-4 py-3 w-full focus:outline-none 
           focus:shadow-nb-sm focus:-translate-x-0.5 focus:-translate-y-0.5;
  }
  
  /* Status */
  .nb-status {
    @apply border-t-3 border-nb-black bg-nb-yellow px-4 py-2 font-bold uppercase text-sm;
  }
  
  /* Token Counter */
  .nb-token-counter {
    @apply border-3 border-nb-black bg-nb-purple text-white px-3 py-1 font-mono text-xs;
  }
}
```

### 3.5 Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ▓▓▓ AGENT-TUI WEB ▓▓▓        [▼ my-project] [+ Add Proj]    │  
├──────────────┬──────────────────────────────────────────────┤
│ ▓ CHATS ▓    │  ▓▓▓ MY-PROJECT ▓▓▓  [+ New Chat]            │
│ ──────────── │  /home/user/projects/my-project               │
│ ▸ Chat 1     │  ─────────────────────────────────────────    │
│ ▸ Chat 2     │                                               │
│ ▸ Chat 3     │  ┌────────────────────────────────────────┐  │
│ ──────────── │  │ 👤 You: How do I refactor this?        │  │
│ [+ New Chat] │  └────────────────────────────────────────┘  │
│              │  ┌────────────────────────────────────────┐  │
│              │  │ 🤖 Assistant: Let me analyze...        │  │
│              │  └────────────────────────────────────────┘  │
│              │                                               │
│              │  ┌────────────────────────────────────────┐  │
│              │  │ > Type message...              [Send]  │  │
│              │  └────────────────────────────────────────┘  │
└──────────────┴──────────────────────────────────────────────┘
```

---

## 4. Project Management

### 4.1 Core Rule
Every chat MUST belong to a project. No unassociated chats allowed.

### 4.2 Data Model

```python
@dataclass
class Project:
    id: str              # UUID
    name: str            # Display name
    path: Path           # Absolute path to project root
    created_at: datetime
    updated_at: datetime

@dataclass  
class ChatSession:
    id: str
    project_id: str      # Required foreign key
    title: str
    created_at: datetime
    updated_at: datetime
```

### 4.3 User Flow

1. **First Launch**: Empty state with "Add Your First Project" CTA
2. **No Project = No Chat**: New Chat button disabled until at least one project exists
3. **Project Context**: All operations (file tools, shell commands) happen within selected project's path
4. **Project Switcher**: Dropdown/sidebar selector filters all chats to current project

### 4.4 Database Schema

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'New Chat',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX idx_chats_project ON chat_sessions(project_id);
```

### 4.5 API Endpoints

```
# Projects
GET    /api/projects              # List all projects
POST   /api/projects              # Create new project
GET    /api/projects/{id}         # Get project details
PATCH  /api/projects/{id}         # Update project name
DELETE /api/projects/{id}         # Delete project (cascades to chats)

# Chats (project-scoped)
GET    /api/projects/{id}/chats   # List chats for project
POST   /api/projects/{id}/chats   # Create new chat in project
GET    /api/chats/{id}            # Get chat details
DELETE /api/chats/{id}            # Delete chat
```

### 4.6 Add Project Modal

Path validation against `DEEPAGENTS_ALLOWED_DIRS` before allowing add.

```
┌─────────────────────────────────┐
│ ▓▓▓ ADD NEW PROJECT ▓▓▓    [X] │
├─────────────────────────────────┤
│                                 │
│  Project Path:                  │
│  ┌─────────────────────────┐    │
│  │ /home/user/projects/    │    │
│  │ my-awesome-app          │    │
│  └─────────────────────────┘    │
│                                 │
│  Display Name:                  │
│  ┌─────────────────────────┐    │
│  │ my-awesome-app          │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ ✅ Path validated       │    │
│  └─────────────────────────┘    │
│                                 │
│     [Cancel]  [Add Project]     │
│                                 │
└─────────────────────────────────┘
```

---

## 5. Error Handling

### 5.1 Error Types

| Error | Display | Recovery |
|-------|---------|----------|
| Validation | Inline red border + message | Fix and retry |
| Connection | Toast notification | Auto-retry (3x exponential backoff) |
| Agent Error | Modal with details | Dismiss and continue |
| Path Not Allowed | Warning banner | Update DEEPAGENTS_ALLOWED_DIRS |

### 5.2 Connection States

| State | UI | Action |
|-------|-----|--------|
| Connecting | Animated ellipsis | Auto-retry |
| Connected | Green dot | Normal |
| Disconnected | Red dot + "Reconnecting..." | Auto-retry |
| Failed | Red alert + manual retry | User clicks retry |

### 5.3 Validation Error Example

```html
<div class="border-3 border-nb-orange bg-orange-50 p-3 mb-4">
  <span class="font-bold">⚠️ Validation Error:</span> Path does not exist
</div>
```

---

## 6. Implementation Notes

### 6.1 Entrypoint

```bash
# New command to start web server
uv run agent-tui --web
# or
uv run agent-web
```

### 6.2 Dependencies to Add

```toml
[project.dependencies]
# Existing...
fastapi = ">=0.115.0"
uvicorn = {extras = ["standard"], version = ">=0.32.0"}
jinja2 = ">=3.1.0"
python-multipart = ">=0.0.17"
websockets = ">=14.0"
```

### 6.3 Build Process

```bash
# Compile Tailwind (development)
npx tailwindcss -i src/agent_tui/web/static/css/app.css \
  -o src/agent_tui/web/static/css/output.css --watch

# Build for production
npx tailwindcss -i src/agent_tui/web/static/css/app.css \
  -o src/agent_tui/web/static/css/output.css --minify
```

### 6.4 Web Adapter Pattern

The `WebAdapter` mirrors the existing `AgentAdapter` but dispatches to WebSocket connections instead of TUI widgets:

```python
class WebAdapter:
    def __init__(self, agent: AgentProtocol, websocket: WebSocket):
        self.agent = agent
        self.ws = websocket
    
    async def run_task(self, message: str, thread_id: str | None = None):
        async for event in self.agent.stream(message, thread_id=thread_id):
            await self._dispatch(event)
    
    async def _dispatch(self, event: AgentEvent):
        match event.type:
            case EventType.MESSAGE_CHUNK:
                await self.ws.send_json({"type": "chunk", "text": event.text})
            # ... etc
```

---

## 7. Acceptance Criteria

- [ ] User can add projects with path validation
- [ ] User cannot create chats without a project
- [ ] All TUI features work in web: chat, tool approval, ask-user, token display
- [ ] Neobrutalist styling throughout (no inline CSS)
- [ ] HTMX for server interactions, Alpine.js for local state
- [ ] WebSocket + SSE for real-time streaming
- [ ] Connection recovery on disconnect
- [ ] Shared session database between TUI and web (for now)

---

## 8. Future Considerations

- TUI deprecation and removal
- Multi-user support (authentication)
- File upload via web interface
- Collaborative editing
- Mobile-responsive layout
