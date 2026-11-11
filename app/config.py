"""Application configuration loaded from environment."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: str = Field(..., min_length=10)
    owner_id: int
    admin_id: int | None = None

    # Secrets at rest
    encryption_key: str = Field(..., min_length=20)

    # Storage
    database_url: str = "sqlite+aiosqlite:///./data/whitebird.db"
    token_store_dir: str = "./data/tokens"

    # Scheduler
    balance_poll_seconds: int = 300
    auto_withdrawal_require_confirm: bool = True

    log_level: str = "INFO"

    @field_validator("owner_id")
    @classmethod
    def _owner_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("owner_id must be a positive Telegram user id")
        return v

    @property
    def data_dir(self) -> Path:
        return Path(self.token_store_dir).parent

    @property
    def token_dir(self) -> Path:
        return Path(self.token_store_dir)

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.token_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
