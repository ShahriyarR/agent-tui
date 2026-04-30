"""TitleGenerator - generates chat titles from conversation context."""

from __future__ import annotations

import logging
from typing import Any

from agent_tui.configurator.settings import settings

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Generates short titles for chat threads based on first Q&A."""

    TITLE_PROMPT = """Based on this conversation, generate a short title (max 40 characters):

User: {user_message}
Assistant: {assistant_response}

Title (max 40 chars, descriptive, no quotes):"""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self) -> Any:
        if self._model is None:
            import os
            from pathlib import Path
            from dotenv import load_dotenv
            from langchain.chat_models import init_chat_model

            env_path = Path(__file__).parent.parent.parent.parent / ".env"
            load_dotenv(env_path)

            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key

            self._model = init_chat_model(
                settings.deepagents_model,
                use_responses_api=False
            )
        return self._model

    async def generate_title(
        self,
        user_message: str,
        assistant_response: str,
    ) -> str:
        """Generate a short title from conversation context."""
        if not user_message and not assistant_response:
            return "Untitled Chat"

        prompt = self.TITLE_PROMPT.format(
            user_message=user_message,
            assistant_response=assistant_response
        )

        try:
            model = self._get_model()
            response = await model.ainvoke(prompt)
            title = response.content if hasattr(response, "content") else str(response)
            title = title.strip()[:40]
            return title or "Untitled Chat"
        except Exception:
            logger.exception("Title generation failed")
            return "Untitled Chat"
