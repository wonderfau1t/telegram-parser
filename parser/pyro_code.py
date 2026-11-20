"""Диагностика через Pyrogram: запрашивает код и показывает тип доставки.

Запуск: TELEGRAM_PROXY_HOST= uv run python pyro_code.py
Внимание: сессия Pyrogram (*.session у него другой формат) несовместима с Telethon.
Этот скрипт — только для проверки доставки кода. Если он сработает,
авторизацию для парсера делайте через uv run python -m src.auth (Telethon).
"""
import asyncio
import traceback

from pyrogram import Client

from src.config import get_settings


async def main():
    settings = get_settings()
    phone = input("Телефон (+7…): ").strip()
    # Пишем во временную сессию, чтобы не трогать parser.session от Telethon
    app = Client("pyro_diag", api_id=settings.api_id, api_hash=settings.api_hash,
                 workdir=".")
    await app.connect()
    try:
        sent = await app.send_code(phone)
        print(f"OK: код отправлен. Тип доставки: {sent.type}. "
              f"Смотрите сервисный чат «Telegram» / SMS в течение минуты.")
    except Exception:
        print("Ошибка:")
        traceback.print_exc()
    finally:
        # не логинились — сессия с auth_key больше не нужна
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
