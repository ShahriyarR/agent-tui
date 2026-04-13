"""Agent protocol — the contract between the TUI and any agent backend."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, AsyncIterator, Protocol, runtime_checkable


class EventType(StrEnum):
    """Types of events an agent can emit."""

    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_END = "message_end"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ASK_USER = "ask_user"
    TOKEN_UPDATE = "token_update"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


@dataclass
class AgentEvent:
    """A single event from the agent. The ``type`` field determines which
    other fields are populated."""

    type: EventType

    # MESSAGE_CHUNK, ERROR
    text: str = ""

    # TOOL_CALL, TOOL_RESULT
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_output: str = ""
    tool_id: str = ""

    # ASK_USER
    question: str = ""

    # TOKEN_UPDATE
    token_count: int = 0
    context_limit: int = 0

    # STATUS_UPDATE
    status_text: str = ""

    # Extensible payload
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AgentProtocol(Protocol):
    """The contract a backend must implement for the TUI to drive it."""

    async def stream(
        self, message: str, *, thread_id: str | None = None
    ) -> AsyncIterator[AgentEvent]:
        """Send a user message, receive a stream of events."""
        ...

    async def approve_tool(self, tool_id: str, approved: bool) -> None:
        """Respond to a TOOL_CALL event (approve or deny)."""
        ...

    async def answer_question(self, answer: str) -> None:
        """Respond to an ASK_USER event."""
        ...

    async def cancel(self) -> None:
        """Cancel the current execution."""
        ...

    async def get_threads(self) -> list[dict[str, Any]]:
        """List available conversation threads."""
        ...

    async def get_models(self) -> list[dict[str, Any]]:
        """List available models."""
        ...

    async def set_model(self, model_name: str) -> None:
        """Switch the active model."""
        ...

    async def get_skills(self) -> list[dict[str, Any]]:
        """List available skills."""
        ...

    async def invoke_skill(self, name: str, args: str) -> None:
        """Invoke a skill by name."""
        ...
