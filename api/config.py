from __future__ import annotations

from pathlib import Path
from pydantic import BaseSettings, field_validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    vector_db_dir: Path = Path("vector_db")
    data_dir: Path = Path("data/santa_barbara")
    openai_model: str = "gpt-3.5-turbo"
    ollama_model: str = "llama2"
    log_level: str = "INFO"
    cors_origins: str = "*"
    server_host: str = "0.0.0.0"
    server_port: int = 5000
    scrape_timeout: float = 10.0
    scrape_max_bytes: int = 100000
    max_message_bytes: int = 4000
    fallback_message: str = (
        "The assistant is running in demo mode. Configure OPENAI_API_KEY for real answers."
    )

    @field_validator("server_port")
    @classmethod
    def _validate_port(cls, v: int) -> int:
        if not (0 < v < 65536):
            raise ValueError("server_port must be between 1 and 65535")
        return v

    @field_validator("scrape_timeout")
    @classmethod
    def _validate_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("scrape_timeout must be positive")
        return v

    @field_validator("scrape_max_bytes")
    @classmethod
    def _validate_max_bytes(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("scrape_max_bytes must be positive")
        return v

    @field_validator("max_message_bytes")
    @classmethod
    def _validate_max_message(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_message_bytes must be positive")
        return v

    @property
    def allowed_origins(self) -> list[str]:
        """Return the CORS origins parsed from ``cors_origins``."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_prefix = ""
        case_sensitive = False
        env_file = ".env"


settings = Settings()
