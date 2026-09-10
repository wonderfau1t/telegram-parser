import asyncio
from functools import partial

import aio_pika
from telethon import events

from src.client import create_client
from src.config import get_settings
from src.messaging import on_latest_request, publish_message


async def main():
    settings = get_settings()
    client = create_client(settings)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Сначала авторизуйте Telegram: docker compose run --rm parser python -m src.auth"
            )
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            await channel.declare_queue(settings.rabbitmq_queue, durable=True)

            chat_id = settings.chat_id.strip()
            source = int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id
            try:
                chat = await client.get_entity(source)
            except ValueError:
                # A new session may not know a channel's access_hash yet.
                await client.get_dialogs()
                chat = await client.get_entity(source)

            @client.on(events.NewMessage(chats=chat))
            async def on_new_message(event):
                await publish_message(channel, settings.rabbitmq_queue, event.message)
                print(f"Получено новое сообщение: {event.message.id}")

            requests = await channel.declare_queue(
                settings.rabbitmq_queue + ".latest_requests", durable=True,
            )
            await requests.consume(partial(
                on_latest_request, client=client, chat=chat, channel=channel,
                queue_name=settings.rabbitmq_queue,
            ))

            print("Ожидание новых постов…", flush=True)
            await client.run_until_disconnected()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПарсер остановлен.")
