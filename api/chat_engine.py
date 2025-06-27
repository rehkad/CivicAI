from __future__ import annotations

"""Wrapper around whichever LLM is available."""

from typing import Iterable

try:
    from langchain.chains import ConversationChain
    from langchain.llms import Ollama
except Exception:  # pragma: no cover - optional dependency
    ConversationChain = None
    Ollama = None

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - optional dependency
    ChatOpenAI = None

from langchain.memory import ConversationBufferMemory


class ChatEngine:
    fallback_message = (
        "The assistant is running in demo mode. Configure an LLM to get real answers."
    )

    def __init__(self) -> None:
        llm = None
        if Ollama:
            try:
                llm = Ollama(model="llama2")
            except Exception:  # pragma: no cover - optional dependency
                llm = None
        if llm is None and ChatOpenAI:
            try:
                llm = ChatOpenAI(temperature=0.7)
            except Exception:  # pragma: no cover - optional dependency
                llm = None

        self.chain = None
        if llm and ConversationChain:
            memory = ConversationBufferMemory()
            self.chain = ConversationChain(llm=llm, memory=memory)

    def _fallback_stream(self, user_input: str) -> Iterable[str]:
        text = f"(demo) You said: {user_input}" if user_input else self.fallback_message
        for ch in text:
            yield ch

    def stream(self, user_input: str) -> Iterable[str]:
        if self.chain:
            llm = self.chain.llm
            if hasattr(llm, "stream"):
                for chunk in llm.stream(user_input):
                    if hasattr(chunk, "content"):
                        yield chunk.content
                    else:
                        yield str(chunk)
                self.chain.memory.save_context({"input": user_input}, {})
                return
            try:
                reply = self.chain.run(user_input)
                for ch in reply:
                    yield ch
                return
            except Exception:  # pragma: no cover - optional dependency
                pass
        yield from self._fallback_stream(user_input)

    def generate(self, user_input: str) -> str:
        return "".join(list(self.stream(user_input)))
