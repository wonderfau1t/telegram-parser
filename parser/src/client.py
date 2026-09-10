from telethon import TelegramClient

from src.config import Settings


def create_client(settings: Settings) -> TelegramClient:
    proxy = None
    if settings.telegram_proxy_host:
        proxy = {
            "proxy_type": "socks5",
            "addr": settings.telegram_proxy_host,
            "port": settings.telegram_proxy_port,
        }
    return TelegramClient(
        settings.api_session_name, settings.api_id, settings.api_hash, proxy=proxy,
    )
