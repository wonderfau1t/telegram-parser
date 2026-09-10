import asyncio
import json

from aio_pika import DeliveryMode, Message

from src.formatting import serialize_entities


async def publish_message(channel, queue_name, message):
    body = {
        "chat_id": message.chat_id,
        "message_id": message.id,
        "date": message.date.isoformat(),
        "text": message.raw_text or "",
        "entities": serialize_entities(message.entities),
    }
    await channel.default_exchange.publish(
        Message(
            body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        ),
        routing_key=queue_name,
    )


async def on_latest_request(request, *, client, chat, channel, queue_name):
    async with request.process(requeue=True):
        try:
            messages = await client.get_messages(chat, limit=1)
            if messages:
                await publish_message(channel, queue_name, messages[0])
                print(f"Последний пост отправлен в очередь: {messages[0].id}", flush=True)
        except Exception:
            # Avoid a tight redelivery loop while Telegram or RabbitMQ is unavailable.
            await asyncio.sleep(5)
            raise
