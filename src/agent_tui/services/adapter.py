"""Adapter bridging AgentProtocol events to TUI widget actions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agent_tui.domain.protocol import AgentEvent, AgentProtocol, EventType

if TYPE_CHECKING:
    pass  # future: type hint for AgentTuiApp

logger = logging.getLogger(__name__)


class AgentAdapter:
    """Dispatches AgentProtocol events to app methods.

    The adapter calls semantic methods on the app object — it never
    touches widgets directly. This keeps it testable with a mock app.
    """

    def __init__(self, agent: AgentProtocol, app: Any) -> None:
        self.agent = agent
        self.app = app

    async def run_task(
        self, message: str, *, thread_id: str | None = None
    ) -> None:
        """Stream events from the agent and dispatch to the app."""
        self.app.set_status("thinking")

        try:
            async for event in self.agent.stream(
                message, thread_id=thread_id
            ):
                await self._dispatch(event)
        except Exception:
            logger.exception("Agent stream error")
            self.app.show_error("Agent stream encountered an unexpected error.")
        finally:
            self.app.set_status("ready")

    async def _dispatch(self, event: AgentEvent) -> None:
        match event.type:
            case EventType.MESSAGE_CHUNK:
                self.app.append_assistant_text(event.text)

            case EventType.MESSAGE_END:
                self.app.finalize_assistant_message()

            case EventType.TOOL_CALL:
                approved = await self.app.request_tool_approval(
                    tool_name=event.tool_name,
                    tool_args=event.tool_args,
                    tool_id=event.tool_id,
                )
                await self.agent.approve_tool(event.tool_id, approved)

            case EventType.TOOL_RESULT:
                self.app.show_tool_result(
                    event.tool_name, event.tool_output, event.tool_id
                )

            case EventType.ASK_USER:
                answer = await self.app.ask_user(event.question)
                await self.agent.answer_question(answer)

            case EventType.TOKEN_UPDATE:
                self.app.update_token_display(
                    event.token_count, event.context_limit
                )

            case EventType.STATUS_UPDATE:
                self.app.set_status(event.status_text)

            case EventType.ERROR:
                self.app.show_error(event.text)

            case _:
                logger.warning("Unknown event type: %s", event.type)
