from __future__ import annotations

"""Wrapper that attempts to use a real LLM via LangChain."""

from typing import Iterable
import os
import logging
import time

logger = logging.getLogger(__name__)

# Try to import optional language model integrations
try:
    from langchain_openai import ChatOpenAI
    from langchain_community.llms import Ollama
    from openai import OpenAI
    LLM_AVAILABLE = True
except ImportError:
    ChatOpenAI = None
    Ollama = None
    OpenAI = None
    LLM_AVAILABLE = False
    logger.info("LLM integrations not available - running in demo mode")

class ChatEngine:
    """Handle chat completion requests."""

    fallback_message = (
        "The assistant is running in demo mode. Configure OPENAI_API_KEY for real answers."
    )

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3, ollama_model: str | None = None) -> None:
        self.model = model
        self.temperature = temperature
        self.ollama_model = ollama_model or "llama2"
        self.llm = None
        self.client = None
        self.backend: str = "demo"  # one of: openai | ollama | demo
        self._initialize_llm()

    def _initialize_llm(self):
        """Initialize the language model if available."""
        if not LLM_AVAILABLE:
            logger.info("LLM libraries not available - using demo mode")
            return

        # Try OpenAI first
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.llm = ChatOpenAI(model=self.model, temperature=self.temperature, streaming=True)
                self.client = OpenAI(api_key=api_key)
                logger.info(f"Initialized OpenAI with model: {self.model}")
                self.backend = "openai"
                return
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        # Try Ollama as fallback
        try:
            self.llm = Ollama(model=self.ollama_model)
            logger.info(f"Initialized Ollama with model: {self.ollama_model}")
            self.backend = "ollama"
            return
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama: {e}")

        logger.info("No LLM available - using demo mode")
        self.backend = "demo"

    def _fallback_stream(self, user_input: str) -> Iterable[str]:
        """Generate demo response."""
        if not user_input.strip():
            text = self.fallback_message
        else:
            text = f"(demo) You said: {user_input}\n\nThis is a demo response. To get real AI responses, set your OPENAI_API_KEY environment variable."
        
        for ch in text:
            yield ch
            time.sleep(0.01)  # Simulate typing

    def _real_stream(self, user_input: str) -> Iterable[str]:
        """Generate real AI response."""
        if not self.llm:
            yield from self._fallback_stream(user_input)
            return

        try:
            if hasattr(self.llm, 'stream'):
                for chunk in self.llm.stream(user_input):
                    if hasattr(chunk, 'content'):
                        yield chunk.content
                    else:
                        yield str(chunk)
            else:
                response = self.llm.invoke(user_input)
                yield response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            yield from self._fallback_stream(user_input)

    def stream(self, user_input: str, timeout: float = 30.0) -> Iterable[str]:
        """Yield tokens from the LLM with a hard timeout."""
        logger.debug("stream called with: %s", user_input)
        start = time.monotonic()
        
        try:
            if self.llm:
                for token in self._real_stream(user_input):
                    if time.monotonic() - start > timeout:
                        logger.warning("stream timeout reached")
                        break
                    yield token
            else:
                for token in self._fallback_stream(user_input):
                    if time.monotonic() - start > timeout:
                        logger.warning("stream timeout reached")
                        break
                    yield token
        except Exception as e:
            logger.exception("Stream error: %s", e)
            yield "Sorry, I encountered an error. Please try again."

    def generate(self, user_input: str, timeout: float = 30.0) -> str:
        """Generate a complete response."""
        logger.debug("generate called with: %s", user_input)
        try:
            text = "".join(list(self.stream(user_input, timeout=timeout)))
            logger.debug("generate returning: %s", text)
            return text
        except Exception as exc:
            logger.exception("ChatEngine crashed: %s", exc)
            return "Sorry, I encountered an error. Please try again."

    def get_info(self) -> dict:
        """Return current backend/model info."""
        return {
            "backend": self.backend,
            "model": self.model if self.backend != "ollama" else self.ollama_model,
            "temperature": self.temperature,
            "streaming": bool(self.llm),
        }
