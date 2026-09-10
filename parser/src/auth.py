import asyncio

from src.client import create_client
from src.config import get_settings


async def main():
    async with create_client(get_settings()):
        print("Авторизация завершена, сессия сохранена.")


if __name__ == "__main__":
    asyncio.run(main())
