# Thread Title Generator Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-generate thread titles from first user message + first LLM response, using async non-blocking title generation.

**Architecture:**
1. `EventTranslator` detects first assistant complete on `on_chain_end` → emits `TITLE_REQUESTED` `AgentEvent`
2. `DeepAgentsAdapter.stream()` passes `thread_id` in `TITLE_REQUESTED`
3. `WebAdapter` handles `TITLE_REQUESTED` by spawning background title generation task
4. Background task calls `SessionStore.update_chat(thread_id, title)` to persist title
5. Simple reload: user navigates to new messages naturally; no special UI refresh needed

**Simplification:** Title generation is async and non-critical. If it fails, "Untitled Chat" remains. No need for complex HTMX refresh — the title appears on next page load.

**Tech Stack:** DeepAgents, LangGraph, FastAPI, aiosqlite

---

## Chunk 1: Add TITLE_REQUESTED Event Type

**Files:**
- Modify: `src/agent_tui/domain/protocol.py`

- [ ] **Step 1: Add TITLE_REQUESTED to EventType enum**

```python
class EventType(Enum):
    # ... existing types ...
    TITLE_REQUESTED = "title_requested"
```

- [ ] **Step 2: Add fields to AgentEvent dataclass**

```python
@dataclass
class AgentEvent:
    # ... existing fields ...
    user_message: str = ""
    assistant_response: str = ""
    thread_id: str = ""
```

- [ ] **Step 3: Commit**

```bash
git add src/agent_tui/domain/protocol.py
git commit -m "feat: add TITLE_REQUESTED event type"
```

---

## Chunk 2: EventTranslator Message Extraction

**Files:**
- Modify: `src/agent_tui/services/deep_agents/event_translator.py`

- [ ] **Step 1: Add __init__ with state tracking**

```python
class EventTranslator:
    def __init__(self) -> None:
        """Initialize translator with state for title generation tracking."""
        self._first_human_content: str = ""
        self._first_ai_content: str = ""
        self._emitted_title_requested: bool = False
```

- [ ] **Step 2: Track messages in _handle_chat_model_stream**

In `_handle_chat_model_stream`, track first assistant content as chunks come in:

```python
def _handle_chat_model_stream(self, data: dict[str, Any], event: dict[str, Any]) -> Iterator[AgentEvent]:
    """Handle on_chat_model_stream events for message chunks from chat models."""
    chunk = data.get("chunk")
    if chunk is None:
        return

    content = ""
    if hasattr(chunk, "content"):
        content = chunk.content
    elif isinstance(chunk, dict):
        content = chunk.get("content", "")

    if content and isinstance(content, str):
        # Track first assistant response chunks
        if not self._first_ai_content:
            self._first_ai_content = content
        yield AgentEvent(
            type=EventType.MESSAGE_CHUNK,
            text=content,
        )
```

- [ ] **Step 3: Extract first human from event metadata**

Actually, we need to track first human differently. Looking at the event structure for `on_chain_stream`, the first human message comes as a special event before chat model starts. Let me check actual structure...

Simplify: track `user_message` passed to `stream()` in the adapter, not in translator. Translator only tracks when first assistant completes.

- [ ] **Step 4: Add _handle_chain_end logic for TITLE_REQUESTED**

Update `_handle_chain_end`:

```python
def _handle_chain_end(
    self, data: dict[str, Any], event: dict[str, Any], data_present: bool
) -> Iterator[AgentEvent]:
    """Handle on_chain_end events for message end."""
    if not data_present:
        return
    yield AgentEvent(type=EventType.MESSAGE_END)

    # Emit TITLE_REQUESTED if we have first messages
    # Note: user_message should be set by adapter before streaming
    if self._first_ai_content and not self._emitted_title_requested:
        self._emitted_title_requested = True
        yield AgentEvent(
            type=EventType.TITLE_REQUESTED,
            user_message="",  # Adapter sets this via separate mechanism
            assistant_response=self._first_ai_content[:200],
            thread_id="",  # Adapter sets this
        )
```

Issue: We need first human content too. Better approach: extract from checkpoint in `_handle_chain_end`.

- [ ] **Step 5: Extract first human from checkpoint data**

```python
def _handle_chain_end(
    self, data: dict[str, Any], event: dict[str, Any], data_present: bool
) -> Iterator[AgentEvent]:
    """Handle on_chain_end events for message end."""
    if not data_present:
        return
    yield AgentEvent(type=EventType.MESSAGE_END)

    if self._first_ai_content and not self._emitted_title_requested:
        # Extract first human from checkpoint
        first_human = self._extract_first_human(data)
        if first_human:
            self._emitted_title_requested = True
            yield AgentEvent(
                type=EventType.TITLE_REQUESTED,
                user_message=first_human[:40],
assistant_response=self._first_ai_content[:40],
                thread_id="",
            )

def _extract_first_human(self, data: dict) -> str | None:
    """Extract first human message content from checkpoint data."""
    try:
        channel_values = data.get("channel_values", {})
        messages = channel_values.get("messages", [])
        for msg in messages:
            msg_type = getattr(msg, "type", None)
            if msg_type in ("human", "user", "HumanMessage"):
                content = getattr(msg, "content", "")
                if isinstance(content, str):
                    return content
                # Handle dict content
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            return part.get("text", "")
    except Exception:
        logger.debug("Failed to extract first human from checkpoint")
    return None
```

- [ ] **Step 6: Commit**

```bash
git add src/agent_tui/services/deep_agents/event_translator.py
git commit -m "feat: track first messages and emit TITLE_REQUESTED"
```

---

## Chunk 3: DeepAgentsAdapter passes thread_id

**Files:**
- Modify: `src/agent_tui/services/deep_agents/adapter.py`

- [ ] **Step 1: Pass thread_id in TITLE_REQUESTED**

In `DeepAgentsAdapter.stream()`, find where `TITLE_REQUESTED` events are yielded and set thread_id:

```python
# In the yield statement for TITLE_REQUESTED events from translator:
yield AgentEvent(
    type=EventType.TITLE_REQUESTED,
    user_message=event.user_message,  # Pass through
    assistant_response=event.assistant_response,  # Pass through
    thread_id=thread_id or "default",  # Set thread_id here
)
```

Actually, the adapter just passes through events from translator. The translator doesn't have access to thread_id. So the adapter needs to patch thread_id after receiving from translator.

Simplest: iterate events after translator, patch thread_id:

```python
async for event in agent.astream_events(...):
    # ... existing handling ...
    for agent_event in agent_events:
        # Patch thread_id for TITLE_REQUESTED
        if agent_event.type == EventType.TITLE_REQUESTED:
            agent_event.thread_id = thread_id or "default"
        yield agent_event
```

- [ ] **Step 2: Commit**

```bash
git add src/agent_tui/services/deep_agents/adapter.py
git commit -m "feat: pass thread_id in TITLE_REQUESTED events"
```

---

## Chunk 4: Title Generator

**Files:**
- Create: `src/agent_tui/services/deep_agents/title.py`
- Tests: `tests/services/deep_agents/test_title.py`

- [ ] **Step 1: Write failing test**

```python
# tests/services/deep_agents/test_title.py
import pytest
from agent_tui.services.deep_agents.title import TitleGenerator


@pytest.fixture
def title_generator():
    return TitleGenerator()


@pytest.mark.asyncio
async def test_generate_title_returns_string(title_generator):
    result = await title_generator.generate_title(
        user_message="Create FastAPI endpoint in main.py",
        assistant_response="I'll create a FastAPI endpoint for you..."
    )
    assert isinstance(result, str)
    assert len(result) <= 40


@pytest.mark.asyncio
async def test_generate_title_handles_empty(title_generator):
    result = await title_generator.generate_title("", "")
    assert result == "Untitled Chat"
```

Run: `pytest tests/services/deep_agents/test_title.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 2: Create TitleGenerator**

```python
"""TitleGenerator - generates chat titles from conversation context."""

from __future__ import annotations

import logging

from agent_tui.configurator.settings import settings

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Generates short titles for chat threads based on first Q&A."""

    TITLE_PROMPT = """Based on this conversation, generate a short title (max 40 characters):

User: {user_message}
Assistant: {assistant_response}

Title (max 40 chars, descriptive, no quotes):"""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self) -> Any:
        if self._model is None:
            from langchain.chat_models import init_chat_model

            self._model = init_chat_model(
                settings.deepagents_model,
                use_responses_api=False
            )
        return self._model

    async def generate_title(
        self,
        user_message: str,
        assistant_response: str,
    ) -> str:
        """Generate a short title from conversation context."""
        if not user_message and not assistant_response:
            return "Untitled Chat"

        prompt = self.TITLE_PROMPT.format(
            user_message=user_message,
            assistant_response=assistant_response
        )

        try:
            model = self._get_model()
            response = await model.ainvoke(prompt)
            title = response.content if hasattr(response, "content") else str(response)
            title = title.strip()[:40]
            return title or "Untitled Chat"
        except Exception:
            logger.exception("Title generation failed")
            return "Untitled Chat"
```

Run: `pytest tests/services/deep_agents/test_title.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/agent_tui/services/deep_agents/title.py tests/services/deep_agents/test_title.py
git commit -m "feat: add TitleGenerator"
```

---

## Chunk 5: WebAdapter handles TITLE_REQUESTED

**Files:**
- Modify: `src/agent_tui/services/web_adapter.py`

- [ ] **Step 1: Add TITLE_REQUESTED handling**

In `_dispatch`, add:

```python
case EventType.TITLE_REQUESTED:
    asyncio.create_task(self._generate_title(
        event.user_message,
        event.assistant_response,
        event.thread_id,
    ))
```

- [ ] **Step 2: Add _generate_title method**

```python
async def _generate_title(
    self,
    user_message: str,
    assistant_response: str,
    thread_id: str,
) -> None:
    """Generate title in background and update store."""
    from agent_tui.services.deep_agents.title import TitleGenerator
    from agent_tui.web.routes.api import get_session_store

    try:
        generator = TitleGenerator()
        title = await generator.generate_title(
            user_message=user_message,
            assistant_response=assistant_response,
        )
        store = get_session_store()
        await store.update_chat(thread_id, title)
    except Exception:
        logger.exception("Background title generation failed")
```

- [ ] **Step 3: Commit**

```bash
git add src/agent_tui/services/web_adapter.py
git commit -m "feat: handle TITLE_REQUESTED with background title generation"
```

---

## Chunk 6: UI Placeholder

**Files:**
- Modify: `src/agent_tui/web/routes/api.py` — create chat with "Generating title..." placeholder
- Modify: `src/agent_tui/web/templates/chat.html` — show spinner until title updates

- [ ] **Step 1: Create chat with placeholder title**

When creating a new chat via API, set initial title to "Generating title...":

```python
async def create_chat(title: str = "Generating title...", project_id: str | None = None):
    # ... existing code ...
```

- [ ] **Step 2: Update sidebar CSS for title wrapping**

In `chat.html` sidebar chat list item, ensure titles wrap properly:

```css
/* In <style> section or inline */
.chat-title {
    word-break: break-word;
    white-space: normal;
    overflow-wrap: break-word;
}
```

The title will display fully even if it exceeds 40 chars, wrapping to new line as needed.

- [ ] **Step 3: Commit**

```bash
git add src/agent_tui/web/routes/api.py src/agent_tui/web/templates/chat.html
git commit -m "feat: show generating title placeholder with wrapping support"
```

---

## Verification

Run: `pytest tests/ -v --tb=short`
Manual test: Create new chat, send message, observe title generation
