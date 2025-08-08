from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


@dataclass(frozen=True)
class Settings:
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _get_int("PORT", 8000)

    # Chat / LLM
    model_name: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    model_temperature: float = _get_float("MODEL_TEMPERATURE", 0.3)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama2")
    chat_timeout_seconds: float = _get_float("CHAT_TIMEOUT_SECONDS", 30.0)

    # Vector DB
    enable_vector_db: bool = _get_bool("ENABLE_VECTOR_DB", True)
    vector_db_dir: str = os.getenv(
        "VECTOR_DB_DIR",
        os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "vector_db")),
    )


settings = Settings()


