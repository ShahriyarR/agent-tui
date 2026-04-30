"""Web adapter - dispatches AgentProtocol events to WebSocket."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from agent_tui.domain.protocol import AgentEvent, AgentProtocol, EventType

logger = logging.getLogger(__name__)


class WebAdapter:
    """Dispatches AgentProtocol events to WebSocket client.
    
    Mirrors the existing AgentAdapter but sends events over WebSocket
    instead of calling TUI widget methods.
    """
    
    def __init__(self, agent: AgentProtocol, websocket: WebSocket) -> None:
        self.agent = agent
        self.websocket = websocket
    
    async def run_task(self, message: str, *, thread_id: str | None = None) -> None:
        """Stream events from agent and dispatch to WebSocket."""
        logger.info(f"[WEB_ADAPTER] Starting run_task for thread: {thread_id}")
        await self._send_status("thinking")

        event_count = 0
        try:
            async for event in self.agent.stream(message, thread_id=thread_id):
                event_count += 1
                logger.debug(f"[WEB_ADAPTER] Dispatching event {event_count}: {event.type}")
                await self._dispatch(event)
        except Exception:
            logger.exception("Agent stream error")
            await self._send_error("Agent stream encountered an unexpected error.")
        finally:
            logger.info(f"[WEB_ADAPTER] Completed run_task. Dispatched {event_count} events.")
            await self._send_status("ready")
    
    async def _dispatch(self, event: AgentEvent) -> None:
        """Dispatch a single event to the WebSocket."""
        logger.debug("[WEB DISPATCH] Event type: %s", event.type)
        
        match event.type:
            case EventType.MESSAGE_CHUNK:
                await self.websocket.send_json({
                    "type": "chunk",
                    "text": event.text
                })
            
            case EventType.MESSAGE_END:
                await self.websocket.send_json({"type": "message_end"})
            
            case EventType.TOOL_CALL:
                await self.websocket.send_json({
                    "type": "tool_call",
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_args": event.tool_args
                })
            
            case EventType.TOOL_RESULT:
                await self.websocket.send_json({
                    "type": "tool_result",
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_output": event.tool_output
                })
            
            case EventType.ASK_USER:
                await self.websocket.send_json({
                    "type": "ask_user",
                    "question": event.question,
                    "metadata": event.metadata
                })
            
            case EventType.TOKEN_UPDATE:
                await self.websocket.send_json({
                    "type": "token_update",
                    "token_count": event.token_count,
                    "context_limit": event.context_limit
                })
            
            case EventType.STATUS_UPDATE:
                await self._send_status(event.status_text)
            
            case EventType.ERROR:
                await self._send_error(event.text)
            
            case EventType.PLAN_STEP:
                await self.websocket.send_json({
                    "type": "plan_step",
                    "text": event.plan_step_text,
                    "current": event.plan_current_step,
                    "total": event.plan_total_steps
                })
            
            case EventType.SUBAGENT_START:
                await self.websocket.send_json({
                    "type": "subagent_start",
                    "name": event.subagent_name
                })
            
            case EventType.SUBAGENT_END:
                await self.websocket.send_json({
                    "type": "subagent_end",
                    "name": event.subagent_name
                })
            
            case EventType.CONTEXT_SUMMARIZED:
                await self.websocket.send_json({
                    "type": "context_summarized",
                    "token_count": event.token_count
                })
            
            case EventType.INTERRUPT:
                await self.websocket.send_json({
                    "type": "interrupt",
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_args": event.tool_args
                })

            case EventType.TITLE_REQUESTED:
                asyncio.create_task(self._generate_title(
                    event.user_message,
                    event.assistant_response,
                    event.thread_id,
                ))

            case _:
                logger.warning("Unknown event type: %s", event.type)
    
    async def _send_status(self, text: str) -> None:
        """Send status update."""
        await self.websocket.send_json({
            "type": "status",
            "text": text
        })
    
    async def _send_error(self, message: str) -> None:
        """Send error message."""
        await self.websocket.send_json({
            "type": "error",
            "message": message
        })

    async def _generate_title(
        self,
        user_message: str,
        assistant_response: str,
        thread_id: str,
    ) -> None:
        """Generate title in background and update store."""
        from agent_tui.services.deep_agents.title import TitleGenerator
        from agent_tui.web.routes.api import get_session_store

        try:
            generator = TitleGenerator()
            title = await generator.generate_title(
                user_message=user_message,
                assistant_response=assistant_response,
            )
            store = get_session_store()
            await store.update_chat(thread_id, title)
        except Exception:
            logger.exception("Background title generation failed")
    
    async def approve_tool(self, tool_id: str, approved: bool) -> None:
        """Forward tool approval to agent."""
        await self.agent.approve_tool(tool_id, approved)
    
    async def answer_question(self, answer: str) -> None:
        """Forward user answer to agent."""
        await self.agent.answer_question(answer)
    
    async def cancel(self) -> None:
        """Cancel current execution."""
        await self.agent.cancel()
