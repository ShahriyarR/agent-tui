"""Agent factory for creating the appropriate agent backend."""

from __future__ import annotations

import os
from typing import Any

from agent_tui.domain.protocol import AgentProtocol


def create_agent(agent_type: str | None = None, *, root_dir: str | None = None) -> AgentProtocol:
    """Create an agent based on type or environment settings.
    
    Args:
        agent_type: Either 'stub' or 'deepagents'. If None, uses environment
                   variable AGENT_TUI_WEB_AGENT or defaults to 'stub'.
        root_dir: Root directory for file operations (used by deepagents).
    
    Returns:
        An agent implementing AgentProtocol.
    
    Raises:
        ValueError: If agent_type is invalid.
        RuntimeError: If DeepAgents is requested but not available.
    """
    if agent_type is None:
        agent_type = os.environ.get('AGENT_TUI_WEB_AGENT', 'stub')
    
    match agent_type:
        case 'stub':
            from agent_tui.services.stub_agent import StubAgent
            return StubAgent()
        
        case 'deepagents':
            try:
                from agent_tui.services.deep_agents import DeepAgentsAdapter
                if root_dir:
                    return DeepAgentsAdapter(
                        model=os.environ.get('AGENT_TUI_MODEL', 'openai:gpt-4o'),
                        root_dir=root_dir
                    )
                return DeepAgentsAdapter.from_settings()
            except ImportError as e:
                raise RuntimeError(
                    "DeepAgents is not installed. "
                    "Install it with: uv add deepagents\n"
                    f"Original error: {e}"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to initialize DeepAgents: {e}\n"
                    "Make sure OPENAI_API_KEY is set."
                )
        
        case _:
            raise ValueError(f"Unknown agent type: {agent_type}. Use 'stub' or 'deepagents'.")
