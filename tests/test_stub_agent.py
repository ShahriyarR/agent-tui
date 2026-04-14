"""Tests for StubAgent."""

import asyncio

import pytest

from agent_tui.domain.protocol import AgentEvent, EventType
from agent_tui.services.stub_agent import StubAgent


@pytest.fixture
def agent() -> StubAgent:
    return StubAgent()


@pytest.mark.asyncio
async def test_stream_emits_message_chunks(agent: StubAgent):
    """First message should include MESSAGE_CHUNK events."""
    events: list[AgentEvent] = []

    async def _drain():
        async for event in agent.stream("hello"):
            events.append(event)
            if event.type == EventType.TOOL_CALL:
                await agent.approve_tool(event.tool_id, True)

    await _drain()

    chunk_events = [e for e in events if e.type == EventType.MESSAGE_CHUNK]
    assert len(chunk_events) > 0
    combined = "".join(e.text for e in chunk_events)
    assert len(combined) > 0


@pytest.mark.asyncio
async def test_stream_ends_with_message_end(agent: StubAgent):
    """Stream should always end with MESSAGE_END."""
    events: list[AgentEvent] = []

    async def _drain():
        async for event in agent.stream("hello"):
            events.append(event)
            if event.type == EventType.TOOL_CALL:
                await agent.approve_tool(event.tool_id, True)
            elif event.type == EventType.ASK_USER:
                await agent.answer_question("test answer")

    await _drain()
    assert events[-1].type == EventType.MESSAGE_END


@pytest.mark.asyncio
async def test_stream_message_1_has_tool_call(agent: StubAgent):
    """First message should include a TOOL_CALL event."""
    events: list[AgentEvent] = []

    async def _drain():
        async for event in agent.stream("hello"):
            events.append(event)
            if event.type == EventType.TOOL_CALL:
                await agent.approve_tool(event.tool_id, True)

    await _drain()

    tool_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert len(tool_events) == 1
    assert tool_events[0].tool_name != ""
    assert tool_events[0].tool_id != ""


@pytest.mark.asyncio
async def test_stream_message_2_has_ask_user(agent: StubAgent):
    """Second message should include an ASK_USER event."""
    # Drain first message
    async for event in agent.stream("first"):
        if event.type == EventType.TOOL_CALL:
            await agent.approve_tool(event.tool_id, True)

    # Second message
    events: list[AgentEvent] = []
    async for event in agent.stream("second"):
        events.append(event)
        if event.type == EventType.ASK_USER:
            await agent.answer_question("yes")

    ask_events = [e for e in events if e.type == EventType.ASK_USER]
    assert len(ask_events) == 1
    assert ask_events[0].question != ""


@pytest.mark.asyncio
async def test_stream_message_3_has_error(agent: StubAgent):
    """Third message should include an ERROR event."""
    # Drain first two messages
    async for event in agent.stream("first"):
        if event.type == EventType.TOOL_CALL:
            await agent.approve_tool(event.tool_id, True)
    async for event in agent.stream("second"):
        if event.type == EventType.ASK_USER:
            await agent.answer_question("yes")

    # Third message
    events: list[AgentEvent] = []
    async for event in agent.stream("third"):
        events.append(event)

    error_events = [e for e in events if e.type == EventType.ERROR]
    assert len(error_events) == 1
    assert error_events[0].text != ""


@pytest.mark.asyncio
async def test_stream_includes_token_update(agent: StubAgent):
    """Stream should include TOKEN_UPDATE events."""
    events: list[AgentEvent] = []
    async for event in agent.stream("hello"):
        events.append(event)
        if event.type == EventType.TOOL_CALL:
            await agent.approve_tool(event.tool_id, True)

    token_events = [e for e in events if e.type == EventType.TOKEN_UPDATE]
    assert len(token_events) >= 1
    assert token_events[0].token_count > 0
    assert token_events[0].context_limit > 0


@pytest.mark.asyncio
async def test_tool_call_blocks_until_approved(agent: StubAgent):
    """TOOL_CALL should block the stream until approve_tool is called."""
    got_tool_call = asyncio.Event()
    got_tool_result = asyncio.Event()

    async def _consume():
        async for event in agent.stream("hello"):
            if event.type == EventType.TOOL_CALL:
                got_tool_call.set()
            elif event.type == EventType.TOOL_RESULT:
                got_tool_result.set()

    task = asyncio.create_task(_consume())

    await asyncio.wait_for(got_tool_call.wait(), timeout=5.0)
    assert not got_tool_result.is_set()

    await agent.approve_tool("tool_1", True)
    await asyncio.wait_for(got_tool_result.wait(), timeout=5.0)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_get_threads_returns_list(agent: StubAgent):
    threads = await agent.get_threads()
    assert isinstance(threads, list)
    assert len(threads) >= 2
    assert "id" in threads[0]
    assert "title" in threads[0]


@pytest.mark.asyncio
async def test_get_models_returns_list(agent: StubAgent):
    models = await agent.get_models()
    assert isinstance(models, list)
    assert len(models) >= 2
    assert "name" in models[0]
    assert "provider" in models[0]


@pytest.mark.asyncio
async def test_get_skills_returns_list(agent: StubAgent):
    skills = await agent.get_skills()
    assert isinstance(skills, list)
    assert len(skills) >= 2
    assert "name" in skills[0]
    assert "description" in skills[0]


@pytest.mark.asyncio
async def test_cancel(agent: StubAgent):
    """Cancel should not raise."""
    await agent.cancel()
