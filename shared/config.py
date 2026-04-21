"""Muhit o'zgaruvchilari (Pydantic Settings)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(url: str) -> str:
    """Railway / boshqa provayderlar `postgresql://` beradi; asyncpg `+asyncpg` talab qiladi."""
    u = url.strip()
    low = u.lower()
    if "sqlite" in low:
        return u
    if low.startswith("postgresql+asyncpg://"):
        return u
    for prefix in ("postgres://", "postgresql://"):
        if low.startswith(prefix):
            return "postgresql+asyncpg://" + u[len(prefix) :]
    return u


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    admin_chat_id: int
    # Standart: docker-compose.yml dagi PostgreSQL (usta / usta_dev_change / usta_bot)
    # SQLite: sqlite+aiosqlite:///./data/app.db
    database_url: str = (
        "postgresql+asyncpg://usta:usta_dev_change@localhost:5432/usta_bot"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: object) -> object:
        if isinstance(v, str):
            return _normalize_database_url(v)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
