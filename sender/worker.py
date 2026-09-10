import asyncio
import json
import logging

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractIncomingMessage
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import LinkPreviewOptions, MessageEntity

logger = logging.getLogger(__name__)


async def request_latest_post(channel, queue_name: str):
    requests = await channel.declare_queue(queue_name + ".latest_requests", durable=True)
    await channel.default_exchange.publish(
        Message(body=b"latest", delivery_mode=DeliveryMode.PERSISTENT),
        routing_key=requests.name,
    )


async def on_message(message: AbstractIncomingMessage, bot: Bot, chats: set[int]):
    async with message.process(requeue=True):
        try:
            post = json.loads(message.body)
            text = post.get("text") if isinstance(post, dict) else None
            if not isinstance(text, str) or not text.strip():
                logger.warning("Пропущено сообщение без текста")
                return
            entity_data = post.get("entities", [])
            if not isinstance(entity_data, list):
                raise ValueError("entities must be an array")
            entities = [MessageEntity.model_validate(entity) for entity in entity_data]
        except (ValueError, UnicodeError):
            logger.warning("Пропущено сообщение с некорректным JSON или entities")
            return

        # Keep the message unacknowledged until at least one chat is connected.
        while not chats:
            await asyncio.sleep(1)

        # Snapshot avoids changing the collection while a send is in progress.
        for chat_id in chats.copy():
            while chat_id in chats:
                try:
                    await bot.send_message(
                        chat_id=chat_id, text=text, entities=entities, parse_mode=None,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                    )
                    break
                except TelegramRetryAfter as exc:
                    await asyncio.sleep(exc.retry_after)
                except TelegramAPIError:
                    logger.warning("Ошибка отправки в чат %s; повтор через 5 секунд", chat_id)
                    await asyncio.sleep(5)
