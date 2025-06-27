from __future__ import annotations

"""Wrapper that attempts to use a real LLM via LangChain."""

from typing import Iterable
import os
try:  # optional dependencies - ignore import failures during docs builds
    from langchain_openai import ChatOpenAI
    from langchain_community.llms import Ollama
except Exception:  # pragma: no cover - optional dependency
    ChatOpenAI = None
    Ollama = None

try:
    from openai import OpenAI  # used only for fallback if streaming via SDK
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None

class ChatEngine:
    """Handle chat completion requests."""

    fallback_message = (
        "The assistant is running in demo mode. Configure OPENAI_API_KEY for real answers."
    )

    def __init__(self, model: str = "gpt-3.5-turbo") -> None:
        self.model = model
        key = os.getenv("OPENAI_API_KEY")
        self.llm = None
        if key and ChatOpenAI:
            try:
                self.llm = ChatOpenAI(temperature=0.7, streaming=True, openai_api_key=key)
            except Exception:  # pragma: no cover - optional dependency
                self.llm = None
        elif Ollama:
            try:
                self.llm = Ollama(model="llama2", streaming=True)
            except Exception:  # pragma: no cover - optional dependency
                self.llm = None
        # fallback to OpenAI SDK if available (for backward compatibility)
        self.client = None
        if self.llm is None and key and OpenAI:
            try:
                self.client = OpenAI(api_key=key)
            except Exception:  # pragma: no cover - optional dependency
                self.client = None

    def _fallback_stream(self, user_input: str) -> Iterable[str]:
        text = f"(demo) You said: {user_input}" if user_input else self.fallback_message
        for ch in text:
            yield ch

    def stream(self, user_input: str) -> Iterable[str]:
        if self.llm is not None:
            try:
                for chunk in self.llm.stream(user_input):
                    if hasattr(chunk, "content"):
                        yield chunk.content
                    else:
                        yield str(chunk)
                return
            except Exception:
                pass
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": user_input}],
                    stream=True,
                )
                for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
                return
            except Exception:
                pass
        yield from self._fallback_stream(user_input)

    def generate(self, user_input: str) -> str:
        return "".join(list(self.stream(user_input)))
