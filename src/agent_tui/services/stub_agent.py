"""Stub agent — scripted sequences exercising every TUI feature."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from agent_tui.domain.protocol import AgentEvent, EventType


class StubAgent:
    """Implements AgentProtocol with scripted event sequences.

    Cycles through three scenarios:
      - Message 1 (and 4, 7, ...): tool call flow
      - Message 2 (and 5, 8, ...): ask-user flow
      - Message 3 (and 6, 9, ...): error flow
    """

    def __init__(self) -> None:
        self._message_count = 0
        self._current_model = "stub-model"
        self._cancelled = False
        self._approval_event: asyncio.Event | None = None
        self._approval_result: bool = False
        self._answer_event: asyncio.Event | None = None
        self._user_answer: str = ""

    async def stream(
        self, message: str, *, thread_id: str | None = None
    ) -> AsyncIterator[AgentEvent]:
        self._cancelled = False
        scenario = self._message_count % 3
        self._message_count += 1

        # Opening chunks
        opening = f"I received your message: '{message}'. "
        for word in opening.split():
            if self._cancelled:
                return
            yield AgentEvent(type=EventType.MESSAGE_CHUNK, text=word + " ")
            await asyncio.sleep(0.03)

        if scenario == 0:
            async for event in self._tool_call_flow():
                yield event
        elif scenario == 1:
            async for event in self._ask_user_flow():
                yield event
        elif scenario == 2:
            async for event in self._error_flow():
                yield event

        # Token update
        yield AgentEvent(
            type=EventType.TOKEN_UPDATE,
            token_count=1234 + self._message_count * 500,
            context_limit=128_000,
        )

        yield AgentEvent(type=EventType.MESSAGE_END)

    async def _tool_call_flow(self) -> AsyncIterator[AgentEvent]:
        self._approval_event = asyncio.Event()
        self._approval_result = False

        yield AgentEvent(
            type=EventType.TOOL_CALL,
            tool_id="tool_1",
            tool_name="bash",
            tool_args={"command": "echo 'hello world'"},
        )

        await self._approval_event.wait()
        self._approval_event = None

        if self._approval_result:
            yield AgentEvent(
                type=EventType.TOOL_RESULT,
                tool_id="tool_1",
                tool_name="bash",
                tool_output="hello world",
            )
            follow_up = "The command executed successfully."
        else:
            follow_up = "Tool execution was denied by the user."

        for word in follow_up.split():
            if self._cancelled:
                return
            yield AgentEvent(type=EventType.MESSAGE_CHUNK, text=word + " ")
            await asyncio.sleep(0.03)

    async def _ask_user_flow(self) -> AsyncIterator[AgentEvent]:
        self._answer_event = asyncio.Event()
        self._user_answer = ""

        intro = "I need some clarification before proceeding."
        for word in intro.split():
            if self._cancelled:
                return
            yield AgentEvent(type=EventType.MESSAGE_CHUNK, text=word + " ")
            await asyncio.sleep(0.03)

        yield AgentEvent(
            type=EventType.ASK_USER,
            question="Which approach would you prefer?",
            metadata={
                "choices": [
                    {"label": "Option A", "value": "a"},
                    {"label": "Option B", "value": "b"},
                ]
            },
        )

        await self._answer_event.wait()
        self._answer_event = None

        reply = f"You chose: {self._user_answer}. Continuing with that approach."
        for word in reply.split():
            if self._cancelled:
                return
            yield AgentEvent(type=EventType.MESSAGE_CHUNK, text=word + " ")
            await asyncio.sleep(0.03)

    async def _error_flow(self) -> AsyncIterator[AgentEvent]:
        intro = "Attempting an operation that will fail..."
        for word in intro.split():
            if self._cancelled:
                return
            yield AgentEvent(type=EventType.MESSAGE_CHUNK, text=word + " ")
            await asyncio.sleep(0.03)

        yield AgentEvent(
            type=EventType.ERROR,
            text="Simulated error: connection timed out after 30s",
        )

        recovery = "Recovered from the error. Continuing normally."
        for word in recovery.split():
            if self._cancelled:
                return
            yield AgentEvent(type=EventType.MESSAGE_CHUNK, text=word + " ")
            await asyncio.sleep(0.03)

    async def approve_tool(self, tool_id: str, approved: bool) -> None:
        self._approval_result = approved
        if self._approval_event is not None:
            self._approval_event.set()

    async def answer_question(self, answer: str) -> None:
        self._user_answer = answer
        if self._answer_event is not None:
            self._answer_event.set()

    async def cancel(self) -> None:
        self._cancelled = True
        if self._approval_event is not None:
            self._approval_event.set()
        if self._answer_event is not None:
            self._answer_event.set()

    async def get_threads(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "thread_001",
                "title": "Demo conversation",
                "updated_at": "2026-04-13T10:00:00Z",
                "created_at": "2026-04-13T09:00:00Z",
                "message_count": 12,
            },
            {
                "id": "thread_002",
                "title": "Another session",
                "updated_at": "2026-04-12T15:30:00Z",
                "created_at": "2026-04-12T14:00:00Z",
                "message_count": 5,
            },
            {
                "id": "thread_003",
                "title": "Debugging session",
                "updated_at": "2026-04-11T08:00:00Z",
                "created_at": "2026-04-11T07:00:00Z",
                "message_count": 28,
            },
        ]

    async def get_models(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "stub-model",
                "provider": "stub",
                "context_limit": 128_000,
                "description": "Default stub model",
            },
            {
                "name": "stub-large",
                "provider": "stub",
                "context_limit": 200_000,
                "description": "Large context stub model",
            },
            {
                "name": "stub-fast",
                "provider": "stub",
                "context_limit": 32_000,
                "description": "Fast stub model",
            },
        ]

    async def set_model(self, model_name: str) -> None:
        self._current_model = model_name

    async def get_skills(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "search",
                "description": "Search the web for information",
            },
            {
                "name": "summarize",
                "description": "Summarize a document or URL",
            },
            {
                "name": "analyze",
                "description": "Analyze code or data",
            },
        ]

    async def invoke_skill(self, name: str, args: str) -> None:
        pass
