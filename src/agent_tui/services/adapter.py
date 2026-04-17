"""Adapter bridging AgentProtocol events to TUI widget actions."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agent_tui.domain.protocol import AgentEvent, AgentProtocol, EventType

if TYPE_CHECKING:
    pass  # future: type hint for AgentTuiApp

logger = logging.getLogger(__name__)

FILE_TOOL_NAMES = frozenset({"read_file", "write_file", "edit_file", "glob", "grep"})


def _extract_file_paths_from_tool_args(tool_name: str, tool_args: dict[str, Any]) -> list[Path]:
    """Extract file paths from tool arguments.

    Args:
        tool_name: Name of the file tool.
        tool_args: Dictionary of tool arguments.

    Returns:
        List of file paths extracted from the tool arguments.
    """
    paths: list[Path] = []

    if tool_name in ("read_file", "write_file", "edit_file"):
        if "path" in tool_args:
            paths.append(Path(tool_args["path"]))

    elif tool_name == "glob":
        if "pattern" in tool_args:
            pattern = tool_args["pattern"]
            dir_pattern = pattern
            if "/" in pattern:
                dir_pattern = re.match(r"^(.*)/[^/]+$", pattern)
                if dir_pattern:
                    dir_pattern = dir_pattern.group(1)
                else:
                    dir_pattern = pattern
            if dir_pattern not in (".", "./"):
                paths.append(Path(dir_pattern))

    elif tool_name == "grep":
        if "path" in tool_args:
            paths.append(Path(tool_args["path"]))
        elif "file_paths" in tool_args:
            for fp in tool_args["file_paths"]:
                paths.append(Path(fp))

    return paths


class AgentAdapter:
    """Dispatches AgentProtocol events to app methods.

    The adapter calls semantic methods on the app object — it never
    touches widgets directly. This keeps it testable with a mock app.
    """

    def __init__(self, agent: AgentProtocol, app: Any) -> None:
        self.agent = agent
        self.app = app

    async def run_task(self, message: str, *, thread_id: str | None = None) -> None:
        """Stream events from the agent and dispatch to the app."""
        self.app.set_status("thinking")

        try:
            async for event in self.agent.stream(message, thread_id=thread_id):
                await self._dispatch(event)
        except Exception:
            logger.exception("Agent stream error")
            self.app.show_error("Agent stream encountered an unexpected error.")
        finally:
            self.app.set_status("ready")

    async def _dispatch(self, event: AgentEvent) -> None:
        logger.debug("[DISPATCH] Event type: %s", event.type)
        match event.type:
            case EventType.MESSAGE_CHUNK:
                self.app.append_assistant_text(event.text)

            case EventType.MESSAGE_END:
                self.app.finalize_assistant_message()

            case EventType.TOOL_CALL:
                logger.info("[DISPATCH] TOOL_CALL received: %s (id=%s)", event.tool_name, event.tool_id)
                if event.tool_name in FILE_TOOL_NAMES:
                    logger.info("[DISPATCH] File tool detected: %s", event.tool_name)
                    from agent_tui.configurator.settings import settings

                    paths = _extract_file_paths_from_tool_args(event.tool_name, event.tool_args)
                    for path in paths:
                        if not settings.deepagents_file_tool_allowed(path):
                            logger.warning("[DISPATCH] Path not allowed: %s", path)
                            await self.agent.approve_tool(event.tool_id, False)
                            self.app.show_error(f"Path not allowed: {path}")
                            return

                # Check for dangerous shell commands
                if event.tool_name == "execute":
                    from agent_tui.configurator.settings import (
                        DANGEROUS_SHELL_PATTERNS,
                        contains_dangerous_patterns,
                    )

                    command = event.tool_args.get("command", "")
                    if contains_dangerous_patterns(command):
                        logger.warning("[DISPATCH] Dangerous shell command detected: %s", command)
                        await self.agent.approve_tool(event.tool_id, False)
                        self.app.show_error(
                            f"Command blocked for safety: {command}\n"
                            f"Matches dangerous pattern: {DANGEROUS_SHELL_PATTERNS}"
                        )
                        return

                logger.info("[DISPATCH] Requesting tool approval from app...")
                approved = await self.app.request_tool_approval(
                    tool_name=event.tool_name,
                    tool_args=event.tool_args,
                    tool_id=event.tool_id,
                )
                logger.info("[DISPATCH] Tool approval result: %s", approved)
                await self.agent.approve_tool(event.tool_id, approved)

            case EventType.TOOL_RESULT:
                self.app.show_tool_result(event.tool_name, event.tool_output, event.tool_id)

            case EventType.ASK_USER:
                answer = await self.app.ask_user(event.question)
                await self.agent.answer_question(answer)

            case EventType.TOKEN_UPDATE:
                self.app.update_token_display(event.token_count, event.context_limit)

            case EventType.STATUS_UPDATE:
                self.app.set_status(event.status_text)

            case EventType.ERROR:
                self.app.show_error(event.text)

            case EventType.PLAN_STEP:
                self.app.set_status(
                    f"Planning: step {event.plan_current_step}/{event.plan_total_steps}"
                )
                self.app.show_plan_step(
                    event.plan_step_text,
                    event.plan_current_step,
                    event.plan_total_steps,
                )

            case EventType.SUBAGENT_START:
                name = event.subagent_name or "subagent"
                self.app.set_status(f"Running subagent: {name}")
                self.app.show_subagent_started(name)

            case EventType.SUBAGENT_END:
                self.app.set_status("thinking")
                self.app.show_subagent_finished(event.subagent_name)

            case EventType.CONTEXT_SUMMARIZED:
                self.app.show_context_summarized(event.token_count)

            case EventType.INTERRUPT:
                logger.debug("Agent interrupted")

            case _:
                logger.warning("Unknown event type: %s", event.type)
