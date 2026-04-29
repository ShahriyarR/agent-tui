# Thread Title Generator Design

## Context

The chat UI needs auto-generated titles for threads based on the first user question and the first LLM response. The generation should be async, non-blocking, and flow through the existing event-driven architecture so the UI stays thin.

## Architecture

### Event Flow

```
Adapter.stream() → yields AgentEvent
      ↓
EventTranslator detects "first assistant response complete"
      ↓
Emits internal event: TITLE_REQUESTED { user_message, assistant_response }
      ↓
TitleGenerator (background) listens for TITLE_REQUESTED
      ↓
On title generated → Store.update_chat_title()
      ↓
WebSocket event: { type: "title_updated", chat_id, title }
      ↓
UI (thin): just updates DOM element with new title
```

### Components

| Component | Responsibility |
|-----------|----------------|
| `EventTranslator` | Detect first assistant complete, emit internal `TITLE_REQUESTED` |
| `TitleGenerator` | Background LLM call, update title in store |
| `Store` | Persist title, emit WebSocket event |
| `WebSocket route` | Relay `title_updated` to UI |
| `UI (JS)` | Receive event, update DOM — that's it |

### Trigger

- **When**: After the LLM starts streaming its first response (first `assistant` event complete)
- **Context captured**:
  - `user_message`: First user message in the conversation
  - `assistant_response`: First assistant response (text content)

### Title Generation

- **Implementation**: Direct LLM call (not a full DeepAgents subagent) — YAGNI applies here
- **Prompt template**:
  ```
  Based on this conversation, generate a short title (max 50 chars):
  
  User: {user_message}
  Assistant: {assistant_response}
  
  Title:
  ```
- **Error handling**: If generation fails, keep placeholder title. No retries, no blocking.

### UI Placeholder

- Chat created with placeholder title: `"Generating title..."` with spinner icon
- On `title_updated` event: replace placeholder with actual title, remove spinner

## File Changes

### New Files

- `src/agent_tui/services/deep_agents/title.py` — `TitleGenerator` class
- `src/agent_tui/services/deep_agents/events.py` — Internal event types (e.g., `TITLE_REQUESTED`)

### Modified Files

- `src/agent_tui/services/deep_agents/adapter.py` — Wire `EventTranslator` to emit `TITLE_REQUESTED`
- `src/agent_tui/services/deep_agents/event_translator.py` — Detect first assistant complete, emit `TITLE_REQUESTED`
- `src/agent_tui/services/sessions.py` — Add `update_chat_title()` method
- `src/agent_tui/web/routes/ws.py` — Handle `title_updated` and relay to WebSocket clients
- `src/agent_tui/web/templates/chat.html` — Add spinner element, JS event listener for `title_updated`

## No New API Endpoints

Title flows through existing event system. No new routes needed.
