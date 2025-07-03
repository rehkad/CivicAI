from __future__ import annotations

from pathlib import Path
from pydantic import BaseSettings


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
    fallback_message: str = (
        "The assistant is running in demo mode. Configure OPENAI_API_KEY for real answers."
    )

    @property
    def allowed_origins(self) -> list[str]:
        """Return the CORS origins parsed from ``cors_origins``."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
