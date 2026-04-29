"""WebSocket routes for real-time agent communication."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agent_tui.services.agent_factory import create_agent
from agent_tui.services.web_adapter import WebAdapter
from agent_tui.web.routes.api import get_session_store
from agent_tui.web.state import ConnectionState, connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Global agent cache per project
_project_agents: dict[str, Any] = {}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connections for agent communication."""
    await websocket.accept()
    
    client_id = str(uuid.uuid4())
    store = get_session_store()
    
    # Create connection state
    state = ConnectionState(
        websocket=websocket,
        agent=None  # Will be set per message based on project
    )
    
    # Register connection
    await connection_manager.connect(client_id, state)
    
    # Create adapter (will be updated when agent is set)
    adapter = WebAdapter(None, websocket)
    
    # Track if a task is running
    current_task: asyncio.Task | None = None
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            match msg_type:
                case "chat":
                    user_message = message.get("message", "")
                    thread_id = message.get("thread_id")
                    project_id = message.get("project_id")
                    logger.info(f"[WS] Received chat message: {user_message[:50]}... (thread: {thread_id}, project: {project_id})")

                    # Cancel any existing task
                    if current_task and not current_task.done():
                        logger.info("[WS] Cancelling existing task")
                        await adapter.cancel()
                        current_task.cancel()
                        try:
                            await current_task
                        except asyncio.CancelledError:
                            pass

                    # Get project path and create agent
                    agent_type = os.environ.get('AGENT_TUI_WEB_AGENT', 'stub')
                    root_dir = None
                    
                    if project_id and agent_type == 'deepagents':
                        project = await store.get_project(project_id)
                        if project:
                            root_dir = project.get('path')
                            logger.info(f"[WS] Using project path: {root_dir}")
                    
                    # Create or reuse agent for this project
                    if root_dir and project_id in _project_agents:
                        agent = _project_agents[project_id]
                        logger.info(f"[WS] Reusing cached agent for project {project_id}")
                    else:
                        try:
                            agent = create_agent(agent_type, root_dir=root_dir)
                            logger.info(f"[WS] Created {agent_type} agent with root_dir: {root_dir}")
                            if project_id:
                                _project_agents[project_id] = agent
                        except Exception as e:
                            logger.error(f"[WS] Failed to create agent: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Failed to initialize agent: {e}"
                            })
                            continue
                    
                    # Update state and adapter with agent
                    state.agent = agent
                    adapter.agent = agent

                    # Start streaming response in background task
                    async def run_chat():
                        try:
                            logger.info(f"[WS] Starting agent stream for thread: {thread_id}")
                            await adapter.run_task(user_message, thread_id=thread_id)
                            logger.info("[WS] Agent stream completed")
                        except Exception as e:
                            logger.exception("Chat task error")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Chat error: {str(e)}"
                            })

                    current_task = asyncio.create_task(run_chat())
                
                case "approve_tool":
                    # Forward approval to agent
                    if state.agent:
                        await adapter.approve_tool(
                            message.get("tool_id", ""),
                            message.get("approved", False)
                        )
                
                case "answer":
                    if state.agent:
                        await adapter.answer_question(message.get("answer", ""))
                
                case "cancel":
                    if current_task and not current_task.done():
                        current_task.cancel()
                        try:
                            await current_task
                        except asyncio.CancelledError:
                            pass
                    if state.agent:
                        await adapter.cancel()
                
                case _:
                    logger.warning("Unknown message type: %s", msg_type)
    
    except WebSocketDisconnect:
        logger.info("Client %s disconnected", client_id)
    except Exception:
        logger.exception("WebSocket error")
    finally:
        # Cancel any running task
        if current_task and not current_task.done():
            current_task.cancel()
            try:
                await current_task
            except asyncio.CancelledError:
                pass
        await connection_manager.disconnect(client_id)
