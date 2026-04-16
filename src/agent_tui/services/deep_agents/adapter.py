"""DeepAgentsAdapter — wraps DeepAgents as an AgentProtocol implementation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from agent_tui.domain.protocol import AgentEvent, EventType
from agent_tui.services.deep_agents.event_translator import EventTranslator

logger = logging.getLogger(__name__)


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
        # Real absolute paths usually have multiple components like /home/user/...
        parts = Path(path).parts
        if len(parts) <= 2:  # Just /filename or /dir/filename
            # Convert /test.txt to test.txt (relative to cwd)
            return path.lstrip("/")

    return path


class DeepAgentsAdapter:
    """Implements AgentProtocol by wrapping DeepAgents.

    This adapter uses lazy loading for the DeepAgents package - it attempts
    to import DeepAgents on first use rather than at module load time.
    This allows the TUI to run even if DeepAgents is not installed.

    If DeepAgents is not available, calling stream() will raise an informative
    error explaining that deepagents needs to be installed.
    """

    def __init__(
        self,
        model: str = "openai:gpt-5.2",
        *,
        api_key: str | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            model: The model to use for DeepAgents. Defaults to "openai:o3".
            api_key: Optional API key override.
        """
        self._model = model
        self._api_key = api_key
        self._agent: Any = None
        self._translator = EventTranslator()
        self._deepagents_available: bool
        self._cancelled = False
        self._approval_event: asyncio.Event | None = None
        self._approval_result: bool = False
        self._pending_tool_id: str | None = None
        self._answer_event: asyncio.Event | None = None
        self._user_answer: str = ""

        self._deepagents_available = self._check_deepagents_available()

    @classmethod
    def from_settings(cls) -> "DeepAgentsAdapter":
        """Create adapter from settings.

        Returns:
            DeepAgentsAdapter instance configured from settings.
        """
        from agent_tui.configurator.settings import settings

        return cls(
            model=settings.deepagents_model,
            api_key=settings.openai_api_key,
        )

    def _check_deepagents_available(self) -> bool:
        """Check if DeepAgents package is available."""
        try:
            import deepagents  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_agent(self) -> Any:
        """Ensure the DeepAgents agent is initialized.

        Returns:
            The DeepAgents agent instance (CompiledStateGraph).

        Raises:
            RuntimeError: If DeepAgents is not installed.
        """
        if not self._deepagents_available:
            raise RuntimeError(
                "DeepAgents is not installed. Please install it with:\n"
                "    pip install deepagents\n"
                "Or check that the package is available in your environment."
            )

        if self._agent is None:
            import os
            from pathlib import Path

            from deepagents import create_deep_agent
            from deepagents.backends.filesystem import FilesystemBackend
            from langchain.chat_models import init_chat_model
            from langgraph.checkpoint.memory import MemorySaver

            if self._api_key:
                os.environ["OPENAI_API_KEY"] = self._api_key

            checkpointer = MemorySaver()

            # Disable Responses API to use Chat Completions API instead
            # This accepts bare model names like "gpt-4o" without date suffixes
            model = init_chat_model(self._model, use_responses_api=False)

            # Create filesystem backend rooted at current working directory
            # Virtual mode treats all paths as anchored to root_dir, so /test.txt
            # resolves to <cwd>/test.txt instead of system root /test.txt
            root_dir = Path.cwd()
            backend = FilesystemBackend(root_dir=root_dir, virtual_mode=True)

            self._agent = create_deep_agent(
                model=model,
                checkpointer=checkpointer,
                backend=backend,
            )

        return self._agent

    async def stream(self, message: str, *, thread_id: str | None = None) -> AsyncIterator[AgentEvent]:
        """Send a user message, receive a stream of events.

        Args:
            message: The user message to send.
            thread_id: Optional thread identifier for conversation context.

        Yields:
            AgentEvent objects from the DeepAgents agent, translated via
            EventTranslator.

        Raises:
            RuntimeError: If DeepAgents is not installed.
        """
        if not self._deepagents_available:
            raise RuntimeError(
                "DeepAgents is not installed. Please install it with:\n"
                "    pip install deepagents\n"
                "Or check that the package is available in your environment."
            )

        self._cancelled = False
        self._approval_event = asyncio.Event()
        self._approval_result = False
        self._answer_event = asyncio.Event()
        self._user_answer = ""

        agent = self._ensure_agent()

        config = {"configurable": {"thread_id": thread_id or "default"}}

        try:
            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": message}]},
                config,
            ):
                if self._cancelled:
                    return

                event_type = event.get("event") or event.get("event_type", "unknown")
                logger.debug("[ADAPTER] Raw event from DeepAgents: %s", event_type)

                translated = self._translator.translate(event)
                agent_events = list(translated)
                if agent_events:
                    logger.debug("[ADAPTER] Translated %d events", len(agent_events))
                    for agent_event in agent_events:
                        logger.debug("[ADAPTER] Event type: %s", agent_event.type)

                for agent_event in agent_events:
                    if agent_event.type == EventType.TOOL_CALL:
                        logger.info(
                            "[ADAPTER] TOOL_CALL detected: %s (id=%s)", agent_event.tool_name, agent_event.tool_id
                        )
                        # Set up approval event BEFORE yielding
                        self._approval_event = asyncio.Event()
                        self._pending_tool_id = agent_event.tool_id

                        # YIELD the TOOL_CALL event FIRST so TUI can show approval widget
                        yield agent_event

                        # NOW wait for approval after the event has been dispatched
                        logger.info("[ADAPTER] Waiting for tool approval...")
                        await self._approval_event.wait()
                        if not self._approval_result:
                            logger.info("[ADAPTER] Tool call rejected, skipping results")
                            # Skip subsequent results for this tool call
                            continue
                        logger.info("[ADAPTER] Tool call approved, will show results")
                    else:
                        # Non-tool events are yielded normally
                        yield agent_event

                if event.get("event_type") == "on_chain_end":
                    logger.debug("[ADAPTER] Chain end detected")
                    break
        except Exception as e:
            logger.exception("[ADAPTER] Error in stream")
            yield AgentEvent(
                type="error",
                text=f"DeepAgents error: {str(e)}",
            )

    async def approve_tool(self, tool_id: str, approved: bool) -> None:
        """Respond to a TOOL_CALL event (approve or deny).

        Args:
            tool_id: The ID of the tool call to respond to.
            approved: Whether to approve (True) or deny (False) the tool call.
        """
        self._approval_result = approved
        if self._approval_event is not None:
            self._approval_event.set()

    async def answer_question(self, answer: str) -> None:
        """Respond to an ASK_USER event.

        Args:
            answer: The user's answer to the question.
        """
        self._user_answer = answer
        if self._answer_event is not None:
            self._answer_event.set()

    async def cancel(self) -> None:
        """Cancel the current execution."""
        self._cancelled = True
        if self._approval_event is not None:
            self._approval_event.set()
        if self._answer_event is not None:
            self._answer_event.set()

    async def get_threads(self) -> list[dict[str, Any]]:
        """List available conversation threads.

        Returns:
            A list of thread dictionaries with id, title, updated_at,
            created_at, and message_count fields.
        """
        if not self._deepagents_available:
            return [
                {
                    "id": "thread_default",
                    "title": "Default conversation",
                    "updated_at": "2026-04-14T00:00:00Z",
                    "created_at": "2026-04-14T00:00:00Z",
                    "message_count": 0,
                },
            ]

        return [
            {
                "id": "thread_default",
                "title": "Default conversation",
                "updated_at": "2026-04-14T00:00:00Z",
                "created_at": "2026-04-14T00:00:00Z",
                "message_count": 0,
            },
        ]

    async def get_models(self) -> list[dict[str, Any]]:
        """List available models.

        Returns:
            A list of model dictionaries with name, provider, context_limit,
            and description fields.
        """
        return [
            {
                "name": "openai:gpt-4o",
                "provider": "openai",
                "context_limit": 128_000,
                "description": "OpenAI GPT-4o model",
            },
            {
                "name": "openai:gpt-4o",
                "provider": "openai",
                "context_limit": 128_000,
                "description": "OpenAI GPT-4o Mini model",
            },
            {
                "name": "anthropic:claude-sonnet-4-6",
                "provider": "anthropic",
                "context_limit": 200_000,
                "description": "Anthropic Claude Sonnet 4",
            },
        ]

    async def set_model(self, model_name: str) -> None:
        """Switch the active model.

        Args:
            model_name: The name of the model to switch to.
        """
        self._model = model_name
        self._agent = None

    async def get_skills(self) -> list[dict[str, Any]]:
        """List available skills.

        Returns:
            A list of skill dictionaries with name and description fields.
        """
        if not self._deepagents_available:
            return [
                {
                    "name": "search",
                    "description": "Search the web for information",
                },
                {
                    "name": "summarize",
                    "description": "Summarize a document or URL",
                },
                {
                    "name": "analyze",
                    "description": "Analyze code or data",
                },
            ]

        return [
            {
                "name": "search",
                "description": "Search the web for information",
            },
            {
                "name": "summarize",
                "description": "Summarize a document or URL",
            },
            {
                "name": "analyze",
                "description": "Analyze code or data",
            },
        ]

    async def invoke_skill(self, name: str, args: str) -> None:
        """Invoke a skill by name.

        Args:
            name: The name of the skill to invoke.
            args: Arguments to pass to the skill.
        """
        pass
