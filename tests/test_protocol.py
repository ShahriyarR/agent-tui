"""Tests for AgentProtocol and event types."""

from agent_tui.protocol import AgentEvent, AgentProtocol, EventType


def test_event_type_values():
    assert EventType.MESSAGE_CHUNK == "message_chunk"
    assert EventType.MESSAGE_END == "message_end"
    assert EventType.TOOL_CALL == "tool_call"
    assert EventType.TOOL_RESULT == "tool_result"
    assert EventType.ASK_USER == "ask_user"
    assert EventType.TOKEN_UPDATE == "token_update"
    assert EventType.STATUS_UPDATE == "status_update"
    assert EventType.ERROR == "error"


def test_agent_event_defaults():
    event = AgentEvent(type=EventType.MESSAGE_CHUNK)
    assert event.text == ""
    assert event.tool_name == ""
    assert event.tool_args == {}
    assert event.tool_output == ""
    assert event.tool_id == ""
    assert event.question == ""
    assert event.token_count == 0
    assert event.context_limit == 0
    assert event.status_text == ""
    assert event.metadata == {}


def test_agent_event_message_chunk():
    event = AgentEvent(type=EventType.MESSAGE_CHUNK, text="Hello ")
    assert event.type == EventType.MESSAGE_CHUNK
    assert event.text == "Hello "


def test_agent_event_tool_call():
    event = AgentEvent(
        type=EventType.TOOL_CALL,
        tool_id="t1",
        tool_name="bash",
        tool_args={"command": "ls"},
    )
    assert event.tool_id == "t1"
    assert event.tool_name == "bash"
    assert event.tool_args == {"command": "ls"}


def test_agent_event_metadata_isolation():
    """Each event gets its own metadata dict (no shared default)."""
    e1 = AgentEvent(type=EventType.MESSAGE_CHUNK)
    e2 = AgentEvent(type=EventType.MESSAGE_CHUNK)
    e1.metadata["key"] = "value"
    assert "key" not in e2.metadata


def test_agent_protocol_is_protocol():
    """AgentProtocol should be usable as a typing.Protocol."""
    import typing
    assert issubclass(type(AgentProtocol), type(typing.Protocol))
