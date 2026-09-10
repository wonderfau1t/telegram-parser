from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT.parent / ".env",
        env_file_encoding="utf-8", extra="ignore",
    )
    bot_token: SecretStr
    admin_id: int = Field(gt=0)
    chats_file: Path = ROOT / "chats.json"
    rabbitmq_url: str = "amqp://guest:guest@127.0.0.1:5673/"
    rabbitmq_queue: str = "telegram_posts"
