from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8", extra="ignore",
    )
    api_id: int
    api_hash: str
    api_session_name: str = "parser"
    chat_id: str
    rabbitmq_url: str = "amqp://guest:guest@127.0.0.1:5673/"
    rabbitmq_queue: str = "telegram_posts"
    telegram_proxy_host: str = ""
    telegram_proxy_port: int = 2080


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
