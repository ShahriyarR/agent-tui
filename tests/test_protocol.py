"""Tests for AgentProtocol and event types."""

from agent_tui.domain.protocol import AgentEvent, AgentProtocol, EventType


def test_event_type_values():
    assert EventType.MESSAGE_CHUNK == "message_chunk"
    assert EventType.MESSAGE_END == "message_end"
    assert EventType.TOOL_CALL == "tool_call"
    assert EventType.TOOL_RESULT == "tool_result"
    assert EventType.ASK_USER == "ask_user"
    assert EventType.TOKEN_UPDATE == "token_update"
    assert EventType.STATUS_UPDATE == "status_update"
    assert EventType.ERROR == "error"
    assert EventType.PLAN_STEP == "plan_step"
    assert EventType.SUBAGENT_START == "subagent_start"
    assert EventType.SUBAGENT_END == "subagent_end"
    assert EventType.CONTEXT_SUMMARIZED == "context_summarized"
    assert EventType.INTERRUPT == "interrupt"


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
    assert event.plan_step_text == ""
    assert event.plan_total_steps == 0
    assert event.plan_current_step == 0
    assert event.subagent_name == ""
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


def test_agent_event_plan_step():
    event = AgentEvent(
        type=EventType.PLAN_STEP,
        plan_step_text="Decomposing task into steps",
        plan_total_steps=5,
        plan_current_step=1,
    )
    assert event.type == EventType.PLAN_STEP
    assert event.plan_step_text == "Decomposing task into steps"
    assert event.plan_total_steps == 5
    assert event.plan_current_step == 1


def test_agent_event_subagent_start():
    event = AgentEvent(
        type=EventType.SUBAGENT_START,
        subagent_name="code_writer",
    )
    assert event.type == EventType.SUBAGENT_START
    assert event.subagent_name == "code_writer"


def test_agent_event_subagent_end():
    event = AgentEvent(
        type=EventType.SUBAGENT_END,
        subagent_name="code_writer",
    )
    assert event.type == EventType.SUBAGENT_END
    assert event.subagent_name == "code_writer"


def test_agent_event_context_summarized():
    event = AgentEvent(type=EventType.CONTEXT_SUMMARIZED)
    assert event.type == EventType.CONTEXT_SUMMARIZED


def test_agent_event_interrupt():
    event = AgentEvent(type=EventType.INTERRUPT)
    assert event.type == EventType.INTERRUPT
