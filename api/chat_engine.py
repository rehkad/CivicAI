"""Wrapper that attempts to use a real LLM via LangChain."""

from __future__ import annotations

from typing import Iterable
import logging
import os
import time

# Attempt to import optional language model backends. They may be
# unavailable in offline environments so failures are tolerated.
try:  # pragma: no cover - dependency may be missing
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - optional dependency
    ChatOpenAI = None
try:  # pragma: no cover - dependency may be missing
    from langchain_community.llms import Ollama
except Exception:  # pragma: no cover - optional dependency
    Ollama = None

logger = logging.getLogger(__name__)


class ChatEngine:
    """Handle chat completion requests with optional streaming.

    When no backend model is available the engine falls back to a short demo
    response so the application remains usable in offline environments.
    """

    default_fallback_message = "The assistant is running in demo mode. Configure OPENAI_API_KEY for real answers."

    def __init__(
        self,
        model: str | None = None,
        ollama_model: str | None = None,
        fallback_message: str | None = None,
    ) -> None:
        """Initialize the engine and attempt to configure an LLM backend.

        ``model`` and ``ollama_model`` override the ``OPENAI_MODEL`` and
        ``OLLAMA_MODEL`` environment variables when provided. ``fallback_message``
        customizes the demo response shown when no LLM backend is available.
        """
        env_model = os.getenv("OPENAI_MODEL")
        env_ollama = os.getenv("OLLAMA_MODEL")
        self.model = model or env_model or "gpt-3.5-turbo"
        self.ollama_model = ollama_model or env_ollama or "llama2"
        self.fallback_message = fallback_message or self.default_fallback_message
        self.llm = None
        self._init_llm()

    @property
    def demo_mode(self) -> bool:
        """Return True when no LLM backend is configured."""
        return self.llm is None

    def _init_llm(self) -> None:
        """Select an available LLM backend if possible."""
        if ChatOpenAI and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(model_name=self.model, streaming=True)
                logger.info("Using OpenAI backend: %s", self.model)
                return
            except Exception as exc:  # pragma: no cover - network errors
                logger.warning("Failed to init OpenAI backend: %s", exc)
        if Ollama:
            try:
                self.llm = Ollama(model=self.ollama_model)
                logger.info("Using Ollama backend: %s", self.ollama_model)
                return
            except Exception as exc:  # pragma: no cover - local server errors
                logger.warning("Failed to init Ollama backend: %s", exc)
        logger.info("Falling back to demo mode")

    def _fallback_stream(self, user_input: str) -> Iterable[str]:
        text = f"(demo) You said: {user_input}" if user_input else self.fallback_message
        for ch in text:
            yield ch

    def stream(self, user_input: str, timeout: float = 30.0) -> Iterable[str]:
        """Yield tokens from the LLM with a hard timeout."""
        logger.debug("stream called with: %s", user_input)
        start = time.monotonic()
        iterator: Iterable[str]
        if self.llm is None:
            iterator = self._fallback_stream(user_input)
        else:
            try:
                if hasattr(self.llm, "stream"):
                    iterator = (
                        getattr(chunk, "content", str(chunk))
                        for chunk in self.llm.stream(user_input)
                    )
                else:
                    text = self.llm.invoke(user_input)
                    iterator = iter(str(text))
            except Exception as exc:  # pragma: no cover - runtime failures
                logger.exception("LLM stream failed: %s", exc)
                iterator = self._fallback_stream(user_input)
        for ch in iterator:
            if time.monotonic() - start > timeout:
                logger.warning("stream timeout reached")
                break
            yield ch

    def generate(self, user_input: str, timeout: float = 30.0) -> str:
        logger.debug("generate called with: %s", user_input)
        try:
            text = "".join(self.stream(user_input, timeout=timeout))
            logger.debug("generate returning: %s", text)
            return text
        except Exception as exc:
            logger.exception("ChatEngine crashed: %s", exc)
            return self.fallback_message

    def close(self) -> None:
        """Release resources held by the underlying LLM client if possible."""
        if hasattr(self.llm, "close"):
            try:
                self.llm.close()
            except Exception:
                logger.warning("Failed to close LLM backend", exc_info=True)
