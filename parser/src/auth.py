import asyncio

from src.client import create_client
from src.config import get_settings


async def main():
    client = create_client(get_settings())
    # start() интерактивно запрашивает телефон, код из Telegram и пароль 2FA,
    # если включён, и сохраняет сессию. Требует TTY: docker compose run --rm -T не подойдёт.
    await client.start()
    try:
        me = await client.get_me()
        print(f"Авторизация завершена ({me.first_name}), сессия сохранена.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
