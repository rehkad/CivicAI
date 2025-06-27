from __future__ import annotations

"""Simple wrapper to stream responses from OpenAI's chat API."""

from typing import Iterable
import os
try:
    from openai import OpenAI
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
        self.client = OpenAI(api_key=key) if (key and OpenAI) else None

    def _fallback_stream(self, user_input: str) -> Iterable[str]:
        text = f"(demo) You said: {user_input}" if user_input else self.fallback_message
        for ch in text:
            yield ch

    def stream(self, user_input: str) -> Iterable[str]:
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
