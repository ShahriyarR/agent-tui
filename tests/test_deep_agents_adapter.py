"""Tests for DeepAgentsAdapter."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_tui.domain.protocol import AgentEvent, AgentProtocol, EventType


class MockDeepAgents:
    """Mock DeepAgents module for testing."""

    class Agent:
        """Mock DeepAgents Agent."""

        def __init__(self, model: str = "openai:gpt-4o") -> None:
            self.model = model
            self._threads = [
                {
                    "id": "thread_001",
                    "title": "Test conversation",
                    "updated_at": "2026-04-14T10:00:00Z",
                    "created_at": "2026-04-14T09:00:00Z",
                    "message_count": 5,
                },
            ]
            self._skills = [
                {"name": "search", "description": "Search the web"},
            ]

        async def stream(self, message: str, *, thread_id: str | None = None):
            """Mock stream that yields events."""
            yield {
                "event_type": "on_chain_stream",
                "data": {"name": "content_block_delta", "data": {"content": "Hello "}},
            }
            yield {
                "event_type": "on_chain_stream",
                "data": {"name": "content_block_delta", "data": {"content": "world!"}},
            }
            yield {
                "event_type": "on_tool_start",
                "data": {"name": "bash", "input": {"command": "echo test"}},
                "run_id": "tool_1",
            }
            yield {
                "event_type": "on_chain_end",
                "data": {},
            }

        async def get_threads(self):
            """Mock get_threads."""
            return self._threads

        async def get_skills(self):
            """Mock get_skills."""
            return self._skills

        async def invoke_skill(self, name: str, args: str):
            """Mock invoke_skill."""
            pass


@pytest.fixture
def mock_deepagents_module():
    """Fixture to mock the deepagents module."""
    return MockDeepAgents()


@pytest.fixture
def adapter(mock_deepagents_module):
    """Create adapter with mocked DeepAgents."""
    with patch.dict("sys.modules", {"deepagents": mock_deepagents_module}):
        from agent_tui.services.deep_agents.adapter import DeepAgentsAdapter

        adapter = DeepAgentsAdapter(model="openai:gpt-4o")
        yield adapter


@pytest.fixture
def adapter_without_deepagents():
    """Create adapter when DeepAgents is not available."""
    with patch(
        "agent_tui.services.deep_agents.adapter.DeepAgentsAdapter._check_deepagents_available",
        return_value=False,
    ):
        from agent_tui.services.deep_agents.adapter import DeepAgentsAdapter

        adapter = DeepAgentsAdapter(model="openai:gpt-4o")
        yield adapter


class TestDeepAgentsAdapterAvailable:
    """Tests when DeepAgents is available."""

    def test_implements_agent_protocol(self, adapter):
        """Adapter should implement AgentProtocol."""
        assert isinstance(adapter, AgentProtocol)

    def test_init_sets_model(self, adapter):
        """Init should set the model."""
        assert adapter._model == "openai:gpt-4o"

    def test_deepagents_available_flag_true(self, adapter):
        """_deepagents_available should be True when package is installed."""
        assert adapter._deepagents_available is True

    @pytest.mark.asyncio
    async def test_stream_yields_events(self, adapter):
        """stream() should yield translated AgentEvent objects."""
        events = []
        async for event in adapter.stream("hello"):
            events.append(event)
            if event.type == EventType.TOOL_CALL:
                await adapter.approve_tool(event.tool_id, True)

        assert len(events) > 0
        chunk_events = [e for e in events if e.type == EventType.MESSAGE_CHUNK]
        assert len(chunk_events) >= 2

    @pytest.mark.asyncio
    async def test_stream_includes_message_chunks(self, adapter):
        """stream() should yield MESSAGE_CHUNK events."""
        events = []
        async for event in adapter.stream("hello"):
            events.append(event)
            if event.type == EventType.TOOL_CALL:
                await adapter.approve_tool(event.tool_id, True)

        texts = [e.text for e in events if e.type == EventType.MESSAGE_CHUNK]
        combined = "".join(texts)
        assert "Hello" in combined
        assert "world" in combined

    @pytest.mark.asyncio
    async def test_stream_includes_tool_call(self, adapter):
        """stream() should yield TOOL_CALL events."""
        events = []
        async for event in adapter.stream("hello"):
            events.append(event)
            if event.type == EventType.TOOL_CALL:
                await adapter.approve_tool(event.tool_id, True)

        tool_events = [e for e in events if e.type == EventType.TOOL_CALL]
        assert len(tool_events) >= 1
        assert tool_events[0].tool_name == "bash"

    @pytest.mark.asyncio
    async def test_stream_ends_with_message_end(self, adapter):
        """stream() should end with MESSAGE_END event."""
        events = []
        async for event in adapter.stream("hello"):
            events.append(event)
            if event.type == EventType.TOOL_CALL:
                await adapter.approve_tool(event.tool_id, True)

        assert events[-1].type == EventType.MESSAGE_END

    @pytest.mark.asyncio
    async def test_stream_handles_approval_flow(self, adapter):
        """stream() should handle approve_tool correctly."""
        got_tool_call = asyncio.Event()
        tool_approved = False

        async def consume():
            nonlocal tool_approved
            async for event in adapter.stream("hello"):
                if event.type == EventType.TOOL_CALL:
                    got_tool_call.set()
                    await adapter.approve_tool(event.tool_id, True)
                    tool_approved = True
                elif event.type == EventType.TOOL_RESULT:
                    tool_approved = True

        task = asyncio.create_task(consume())
        await asyncio.wait_for(got_tool_call.wait(), timeout=5.0)
        await asyncio.wait_for(task, timeout=5.0)
        assert tool_approved

    @pytest.mark.asyncio
    async def test_approve_tool_sets_result(self, adapter):
        """approve_tool() should set the approval result."""
        adapter._approval_result = False
        adapter._approval_event = asyncio.Event()

        await adapter.approve_tool("tool_1", True)
        assert adapter._approval_result is True
        assert adapter._approval_event.is_set()

    @pytest.mark.asyncio
    async def test_answer_question_sets_answer(self, adapter):
        """answer_question() should set the user answer."""
        adapter._answer_event = asyncio.Event()
        await adapter.answer_question("test answer")
        assert adapter._user_answer == "test answer"
        assert adapter._answer_event.is_set()

    @pytest.mark.asyncio
    async def test_cancel_sets_cancelled_flag(self, adapter):
        """cancel() should set _cancelled to True."""
        await adapter.cancel()
        assert adapter._cancelled is True

    @pytest.mark.asyncio
    async def test_get_threads_returns_list(self, adapter):
        """get_threads() should return a list of threads."""
        threads = await adapter.get_threads()
        assert isinstance(threads, list)
        assert len(threads) >= 1
        assert "id" in threads[0]
        assert "title" in threads[0]

    @pytest.mark.asyncio
    async def test_get_models_returns_list(self, adapter):
        """get_models() should return a list of models."""
        models = await adapter.get_models()
        assert isinstance(models, list)
        assert len(models) >= 1
        assert "name" in models[0]
        assert "provider" in models[0]

    @pytest.mark.asyncio
    async def test_set_model_changes_model(self, adapter):
        """set_model() should change the model and reset agent."""
        await adapter.set_model("anthropic:claude-3-5-sonnet")
        assert adapter._model == "anthropic:claude-3-5-sonnet"
        assert adapter._agent is None

    @pytest.mark.asyncio
    async def test_get_skills_returns_list(self, adapter):
        """get_skills() should return a list of skills."""
        skills = await adapter.get_skills()
        assert isinstance(skills, list)
        assert len(skills) >= 1
        assert "name" in skills[0]

    @pytest.mark.asyncio
    async def test_invoke_skill_no_error(self, adapter):
        """invoke_skill() should not raise."""
        await adapter.invoke_skill("search", "test query")


class TestDeepAgentsAdapterUnavailable:
    """Tests when DeepAgents is NOT available."""

    def test_deepagents_available_flag_false(self, adapter_without_deepagents):
        """_deepagents_available should be False when package is not installed."""
        assert adapter_without_deepagents._deepagents_available is False

    @pytest.mark.asyncio
    async def test_stream_raises_informative_error(self, adapter_without_deepagents):
        """stream() should raise RuntimeError with helpful message."""
        with pytest.raises(RuntimeError) as exc_info:
            async for _ in adapter_without_deepagents.stream("hello"):
                pass

        assert "deepagents" in str(exc_info.value).lower()
        assert "pip install" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_threads_returns_fallback(self, adapter_without_deepagents):
        """get_threads() should return fallback data when unavailable."""
        threads = await adapter_without_deepagents.get_threads()
        assert isinstance(threads, list)
        assert len(threads) >= 1

    @pytest.mark.asyncio
    async def test_get_models_returns_list(self, adapter_without_deepagents):
        """get_models() should return list even when unavailable."""
        models = await adapter_without_deepagents.get_models()
        assert isinstance(models, list)
        assert len(models) >= 1

    @pytest.mark.asyncio
    async def test_get_skills_returns_fallback(self, adapter_without_deepagents):
        """get_skills() should return fallback skills when unavailable."""
        skills = await adapter_without_deepagents.get_skills()
        assert isinstance(skills, list)
        assert len(skills) >= 1
        assert skills[0]["name"] == "search"

    @pytest.mark.asyncio
    async def test_invoke_skill_does_nothing(self, adapter_without_deepagents):
        """invoke_skill() should do nothing when unavailable."""
        await adapter_without_deepagents.invoke_skill("search", "test")


class TestDeepAgentsAdapterEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_stream_with_none_thread_id(self, adapter):
        """stream() should handle None thread_id."""
        events = []
        async for event in adapter.stream("hello", thread_id=None):
            events.append(event)
            if event.type == EventType.TOOL_CALL:
                await adapter.approve_tool(event.tool_id, True)

        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_approve_tool_without_pending_event(self, adapter):
        """approve_tool() should not raise when no event is pending."""
        await adapter.approve_tool("nonexistent_tool", True)

    @pytest.mark.asyncio
    async def test_answer_question_without_pending_event(self, adapter):
        """answer_question() should not raise when no event is pending."""
        await adapter.answer_question("test")

    @pytest.mark.asyncio
    async def test_cancel_without_pending_events(self, adapter):
        """cancel() should not raise when no events are pending."""
        await adapter.cancel()
        assert adapter._cancelled is True

    @pytest.mark.asyncio
    async def test_model_defaults_to_openai_gpt_4o(self):
        """Default model should be openai:gpt-4o."""
        with patch(
            "agent_tui.services.deep_agents.adapter.DeepAgentsAdapter._check_deepagents_available",
            return_value=True,
        ):
            with patch.dict("sys.modules", {"deepagents": MagicMock()}):
                from agent_tui.services.deep_agents.adapter import DeepAgentsAdapter

                adapter = DeepAgentsAdapter()
                assert adapter._model == "openai:gpt-4o"
