"""Tests for AgentAdapter."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_tui.services.adapter import AgentAdapter
from agent_tui.domain.protocol import AgentEvent, EventType
from agent_tui.services.stub_agent import StubAgent


@pytest.fixture
def mock_app() -> MagicMock:
    app = MagicMock()
    app.append_assistant_text = MagicMock()
    app.finalize_assistant_message = MagicMock()
    app.show_tool_result = MagicMock()
    app.show_error = MagicMock()
    app.update_token_display = MagicMock()
    app.set_status = MagicMock()
    app.request_tool_approval = AsyncMock(return_value=True)
    app.ask_user = AsyncMock(return_value="test answer")
    return app


@pytest.fixture
def agent() -> StubAgent:
    return StubAgent()


@pytest.fixture
def adapter(agent: StubAgent, mock_app: MagicMock) -> AgentAdapter:
    return AgentAdapter(agent=agent, app=mock_app)


@pytest.mark.asyncio
async def test_run_task_streams_text(adapter: AgentAdapter, mock_app: MagicMock):
    await adapter.run_task("hello")
    assert mock_app.append_assistant_text.call_count > 0
    assert mock_app.finalize_assistant_message.call_count == 1


@pytest.mark.asyncio
async def test_run_task_handles_tool_call(adapter: AgentAdapter, mock_app: MagicMock):
    await adapter.run_task("hello")
    mock_app.request_tool_approval.assert_awaited_once()
    mock_app.show_tool_result.assert_called_once()


@pytest.mark.asyncio
async def test_run_task_handles_ask_user(adapter: AgentAdapter, mock_app: MagicMock):
    # First message is tool call, second is ask-user
    await adapter.run_task("first")
    await adapter.run_task("second")
    mock_app.ask_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_task_handles_error(adapter: AgentAdapter, mock_app: MagicMock):
    # First: tool call, second: ask-user, third: error
    await adapter.run_task("first")
    await adapter.run_task("second")
    await adapter.run_task("third")
    mock_app.show_error.assert_called_once()


@pytest.mark.asyncio
async def test_run_task_updates_tokens(adapter: AgentAdapter, mock_app: MagicMock):
    await adapter.run_task("hello")
    mock_app.update_token_display.assert_called_once()
    args = mock_app.update_token_display.call_args
    assert args[0][0] > 0  # token_count
    assert args[0][1] > 0  # context_limit


@pytest.mark.asyncio
async def test_run_task_sets_status(adapter: AgentAdapter, mock_app: MagicMock):
    await adapter.run_task("hello")
    status_calls = [c[0][0] for c in mock_app.set_status.call_args_list]
    assert "thinking" in status_calls
    assert "ready" in status_calls
