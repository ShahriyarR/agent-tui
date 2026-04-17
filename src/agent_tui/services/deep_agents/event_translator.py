"""EventTranslator: DeepAgents/LangGraph checkpoint events → AgentEvent stream."""

from __future__ import annotations

from typing import Any, Iterator

from agent_tui.domain.protocol import AgentEvent, EventType


def _normalize_tool_path(path: str) -> str:
    """Normalize tool paths to be relative to current working directory.

    DeepAgents LLM sometimes generates absolute paths like '/test.txt' which
    would resolve to the filesystem root. This converts them to relative paths
    so they resolve against the current working directory.

    Args:
        path: The path from the tool arguments

    Returns:
        Normalized path (relative if it was absolute root, otherwise unchanged)
    """
    if not path:
        return path

    # If path starts with / but is just /filename (not /home/...), make it relative
    if path.startswith("/") and not path.startswith("//"):
        # Check if it's a real absolute path or just /filename
        # Real absolute paths usually have multiple components
        parts = path.split("/")
        if len(parts) <= 3:  # Just /filename or /dir/filename
            # Convert /test.txt to test.txt (relative to cwd)
            return path.lstrip("/")

    return path


class EventTranslator:
    """Translates DeepAgents/LangGraph checkpoint events to AgentEvent stream.

    This is a pure translation layer with no side effects and no DeepAgents
    dependencies. It works with generic event dict structures that can be
    adapted when DeepAgents is actually integrated.

    Supported events (Phase 1):
        - content_block_delta → MESSAGE_CHUNK
        - on_chain_end → MESSAGE_END
        - on_tool_start → TOOL_CALL
        - on_tool_end → TOOL_RESULT

    Supported events (Phase 5):
        - on_tool_start where tool name is "task" → SUBAGENT_START
        - on_tool_end where tool name is "task" → SUBAGENT_END

    Not translated here (handled upstream or future phases):
        - PLAN_STEP — not produced by LangGraph tool events; handled by adapter dispatch
        - CONTEXT_SUMMARIZED (Phase 6)
        - INTERRUPT (Phase 8)
    """

    def translate(self, event: dict[str, Any]) -> Iterator[AgentEvent]:
        """Translate a raw DeepAgents event dict to AgentEvent stream.

        Args:
            event: Raw event dict with structure:
                {
                    "event": str,  # e.g., "on_chain_stream", "on_tool_start"
                    "data": dict,        # Event-specific payload
                    "run_id": str,       # Optional run identifier
                }

        Yields:
            AgentEvent objects based on the input event type.
        """
        # LangGraph uses "event" key, not "event_type"
        event_type = event.get("event") or event.get("event_type", "")
        data = event.get("data", {})
        data_present = "data" in event

        if event_type == "on_chain_stream":
            yield from self._handle_chain_stream(data, event)
        elif event_type == "on_chat_model_stream":
            yield from self._handle_chat_model_stream(data, event)
        elif event_type == "on_tool_start":
            yield from self._handle_tool_start(data, event)
        elif event_type == "on_tool_end":
            yield from self._handle_tool_end(data, event)
        elif event_type == "on_chain_end":
            yield from self._handle_chain_end(data, event, data_present)
        elif event_type == "on_tool_error":
            yield from self._handle_tool_error(data, event)

    def _handle_chain_stream(self, data: dict[str, Any], event: dict[str, Any]) -> Iterator[AgentEvent]:
        """Handle on_chain_stream events for message chunks."""
        name = data.get("name", "")
        if name == "content_block_delta":
            content = data.get("data", {}).get("content", "")
            if content:
                yield AgentEvent(
                    type=EventType.MESSAGE_CHUNK,
                    text=content,
                )

    def _handle_chat_model_stream(self, data: dict[str, Any], event: dict[str, Any]) -> Iterator[AgentEvent]:
        """Handle on_chat_model_stream events for message chunks from chat models."""
        chunk = data.get("chunk")
        if chunk is None:
            return

        # chunk is typically an AIMessage or AIMessageChunk with .content attribute
        content = ""
        if hasattr(chunk, "content"):
            content = chunk.content
        elif isinstance(chunk, dict):
            content = chunk.get("content", "")

        if content and isinstance(content, str):
            yield AgentEvent(
                type=EventType.MESSAGE_CHUNK,
                text=content,
            )

    def _handle_tool_start(self, data: dict[str, Any], event: dict[str, Any]) -> Iterator[AgentEvent]:
        """Handle on_tool_start events for tool calls."""
        # In LangGraph events, tool name is at top level, not in data
        tool_name = event.get("name", "") or data.get("name", "")
        tool_input = data.get("input", {})
        run_id = event.get("run_id", "")

        if tool_name == "task":
            subagent_name = (
                tool_input.get("description", "")
                or tool_input.get("task", "")
                or "subagent"
            )
            subagent_name = subagent_name[:80]
            yield AgentEvent(type=EventType.SUBAGENT_START, subagent_name=subagent_name)
            return

        if tool_name:
            # Normalize paths in tool arguments to resolve against current directory
            # instead of filesystem root
            normalized_input = dict(tool_input)  # Make a copy

            # Common path argument names used by file tools
            path_keys = ["file_path", "path", "file", "directory", "dir", "pattern", "glob_pattern"]
            for key in path_keys:
                if key in normalized_input and isinstance(normalized_input[key], str):
                    normalized_input[key] = _normalize_tool_path(normalized_input[key])

            # Handle old_string/new_string paths in edit_file
            if tool_name == "edit_file":
                if "old_string" in normalized_input:
                    # Try to extract path from old_string if it contains one
                    pass  # old_string is content, not a path

            yield AgentEvent(
                type=EventType.TOOL_CALL,
                tool_name=tool_name,
                tool_args=normalized_input,
                tool_id=run_id,
            )

    def _handle_tool_end(self, data: dict[str, Any], event: dict[str, Any]) -> Iterator[AgentEvent]:
        """Handle on_tool_end events for tool results."""
        # Get tool name early so task tool check can run regardless of output presence
        tool_name = event.get("name", "") or data.get("name", "")
        run_id = event.get("run_id", "")

        if tool_name == "task":
            yield AgentEvent(type=EventType.SUBAGENT_END, subagent_name="")
            return

        if "output" not in data:
            return
        tool_output = data.get("output")
        if tool_output is None:
            return

        yield AgentEvent(
            type=EventType.TOOL_RESULT,
            tool_name=tool_name,
            tool_id=run_id,
            tool_output=str(tool_output),
        )

    def _handle_chain_end(
        self, data: dict[str, Any], event: dict[str, Any], data_present: bool
    ) -> Iterator[AgentEvent]:
        """Handle on_chain_end events for message end."""
        if not data_present:
            return
        yield AgentEvent(type=EventType.MESSAGE_END)

    def _handle_tool_error(self, data: dict[str, Any], event: dict[str, Any]) -> Iterator[AgentEvent]:
        """Handle on_tool_error events for errors."""
        error_text = data.get("error", str(data))
        yield AgentEvent(
            type=EventType.ERROR,
            text=f"Tool error: {error_text}",
        )
