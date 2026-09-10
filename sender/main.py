import asyncio
import logging
from functools import partial

import aio_pika
from aiogram import Bot, Dispatcher

from config import Settings
from storage import load_chats
from telegram_bot import router
from worker import on_message, request_latest_post


async def main():
    settings = Settings()
    chats = load_chats(settings.chats_file)
    dp = Dispatcher()
    dp.include_router(router)

    async with Bot(token=settings.bot_token.get_secret_value()) as bot:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue = await channel.declare_queue(settings.rabbitmq_queue, durable=True)
            await queue.consume(partial(on_message, bot=bot, chats=chats))
            await bot.delete_webhook(drop_pending_updates=False)
            await request_latest_post(channel, settings.rabbitmq_queue)
            await dp.start_polling(
                bot, settings=settings, chats=chats,
                close_bot_session=False, handle_as_tasks=False,
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
