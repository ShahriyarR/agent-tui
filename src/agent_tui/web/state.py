"""Per-connection state management for web interface."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from agent_tui.domain.protocol import AgentProtocol


@dataclass
class ConnectionState:
    """State for a single WebSocket connection."""
    
    websocket: WebSocket
    agent: AgentProtocol
    current_project_id: str | None = None
    current_thread_id: str | None = None
    pending_approvals: dict[str, asyncio.Event] = field(default_factory=dict)
    pending_answers: dict[str, asyncio.Event] = field(default_factory=dict)
    
    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON message to client."""
        await self.websocket.send_json(data)


class ConnectionManager:
    """Manages all active WebSocket connections."""
    
    def __init__(self) -> None:
        self._connections: dict[str, ConnectionState] = {}
    
    async def connect(self, client_id: str, state: ConnectionState) -> None:
        """Register a new connection."""
        self._connections[client_id] = state
    
    async def disconnect(self, client_id: str) -> None:
        """Remove a connection."""
        if client_id in self._connections:
            del self._connections[client_id]
    
    def get(self, client_id: str) -> ConnectionState | None:
        """Get connection state by client ID."""
        return self._connections.get(client_id)


# Global connection manager instance
connection_manager = ConnectionManager()
