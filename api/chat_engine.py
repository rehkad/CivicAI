from __future__ import annotations

"""Wrapper that attempts to use a real LLM via LangChain."""

from typing import Iterable
import os
import logging

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

    def stream(self, user_input: str) -> Iterable[str]:
        logger.debug("stream called with: %s", user_input)
        # External model integrations disabled; always use fallback
        yield from self._fallback_stream(user_input)

    def generate(self, user_input: str) -> str:
        logger.debug("generate called")
        return "".join(list(self.stream(user_input)))
