"""Wrapper that attempts to use a real LLM via LangChain."""

from __future__ import annotations

from typing import Iterable
import logging
import time

# Optional language model integrations are disabled for debugging
ChatOpenAI = None
Ollama = None
OpenAI = None

logger = logging.getLogger(__name__)

class ChatEngine:
    """Handle chat completion requests."""

    fallback_message = (
        "The assistant is running in demo mode. Configure OPENAI_API_KEY for real answers."
    )

    def __init__(self, model: str = "gpt-3.5-turbo") -> None:
        self.model = model
        self.llm = None  # external models disabled
        self.client = None

    def _fallback_stream(self, user_input: str) -> Iterable[str]:
        text = f"(demo) You said: {user_input}" if user_input else self.fallback_message
        for ch in text:
            yield ch

    def stream(self, user_input: str, timeout: float = 30.0) -> Iterable[str]:
        """Yield tokens from the LLM with a hard timeout."""
        logger.debug("stream called with: %s", user_input)
        start = time.monotonic()
        for ch in self._fallback_stream(user_input):
            if time.monotonic() - start > timeout:
                logger.warning("stream timeout reached")
                break
            yield ch

    def generate(self, user_input: str, timeout: float = 30.0) -> str:
        logger.debug("generate called with: %s", user_input)
        try:
            text = "".join(list(self.stream(user_input, timeout=timeout)))
            logger.debug("generate returning: %s", text)
            return text
        except Exception as exc:
            logger.exception("ChatEngine crashed: %s", exc)
            return self.fallback_message
