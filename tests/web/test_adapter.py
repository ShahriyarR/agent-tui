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
        "metadata": {"choices": [{"label": "A", "value": "a"}]}
    })
