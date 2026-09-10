import asyncio
import json
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import SendMessage

from telegram_bot import on_bot_added, on_bot_removed, register_chat
from worker import on_message, request_latest_post
from storage import load_chats, save_chats


class SenderTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_request_survives_parser_being_offline(self):
        channel = SimpleNamespace(
            declare_queue=AsyncMock(return_value=SimpleNamespace(name="posts.latest_requests")),
            default_exchange=SimpleNamespace(publish=AsyncMock()),
        )
        await request_latest_post(channel, "posts")
        channel.declare_queue.assert_awaited_once_with("posts.latest_requests", durable=True)
        publish = channel.default_exchange.publish
        publish.assert_awaited_once()
        self.assertEqual(publish.await_args.kwargs["routing_key"], "posts.latest_requests")
        self.assertEqual(publish.await_args.args[0].delivery_mode, 2)

    def setUp(self):
        self.chats = set()
        self.bot = SimpleNamespace(send_message=AsyncMock(), leave_chat=AsyncMock())
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.settings = SimpleNamespace(admin_id=123, chats_file=Path(directory.name) / "chats.json")
        self.event = SimpleNamespace(
            chat=SimpleNamespace(id=-100, type="supergroup"),
            from_user=SimpleNamespace(id=123), sender_chat=None, answer=AsyncMock(),
        )
        self.context = AsyncMock()
        self.message = SimpleNamespace(
            body=b'{"text":"hello"}', process=MagicMock(return_value=self.context),
        )

    async def test_owner_adds_chat_and_removal_discards_it(self):
        await on_bot_added(self.event, self.bot, self.settings, self.chats)
        self.assertEqual(self.chats, {-100})
        self.assertEqual(load_chats(self.settings.chats_file), {-100})
        await on_bot_removed(self.event, self.chats, self.settings)
        self.assertEqual(self.chats, set())
        self.assertEqual(load_chats(self.settings.chats_file), set())

    async def test_unauthorized_addition_leaves_and_discards_chat(self):
        self.chats.add(-100)
        self.event.from_user.id = 999
        await on_bot_added(self.event, self.bot, self.settings, self.chats)
        self.assertEqual(self.chats, set())
        self.bot.leave_chat.assert_awaited_once_with(-100)
        self.assertEqual(load_chats(self.settings.chats_file), set())

    async def test_private_chat_is_not_registered(self):
        self.event.chat.type = "private"
        await on_bot_added(self.event, self.bot, self.settings, self.chats)
        self.assertEqual(self.chats, set())

    async def test_register_requires_identifiable_owner(self):
        self.event.from_user.id = 999
        await register_chat(self.event, self.settings, self.chats)
        self.assertFalse(self.chats)
        self.event.from_user.id = 123
        self.event.sender_chat = object()
        await register_chat(self.event, self.settings, self.chats)
        self.assertFalse(self.chats)
        self.event.sender_chat = None
        await register_chat(self.event, self.settings, self.chats)
        self.assertEqual(self.chats, {-100})
        self.assertEqual(load_chats(self.settings.chats_file), {-100})

    def test_storage_restores_chats_and_rejects_invalid_file(self):
        path = self.settings.chats_file
        self.assertEqual(load_chats(path), set())
        save_chats(path, {-100, -200})
        self.assertEqual(load_chats(path), {-100, -200})
        self.assertFalse(path.with_suffix(".json.tmp").exists())
        for invalid in ('{"id": 1}', '[true]', '["-100"]', 'broken'):
            path.write_text(invalid)
            with self.assertRaises(ValueError):
                load_chats(path)
            self.assertEqual(path.read_text(), invalid)

    async def test_broadcast_retries_current_chat_and_acknowledges_after_sending(self):
        self.chats.update({-100, -200})
        self.bot.send_message.side_effect = [
            TelegramRetryAfter(method=SendMessage(chat_id=-100, text="hello"), message="wait", retry_after=0),
            None, None,
        ]
        await on_message(self.message, self.bot, self.chats)
        calls = self.bot.send_message.await_args_list
        self.assertEqual(calls[0].kwargs, calls[1].kwargs)
        self.assertEqual({call.kwargs['chat_id'] for call in calls}, self.chats)
        self.assertEqual(len(calls), 3)
        self.assertIsNone(self.context.__aexit__.await_args.args[0])

    async def test_no_chats_does_not_acknowledge_message(self):
        task = asyncio.create_task(on_message(self.message, self.bot, self.chats))
        await asyncio.sleep(0)
        self.bot.send_message.assert_not_awaited()
        self.context.__aexit__.assert_not_awaited()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_formatting_and_emoji_offsets_are_preserved_without_link_preview(self):
        self.chats.add(-100)
        post = {
            "text": "😀 Жирный и ссылка <tag> *literal*",
            "entities": [
                {"type": "bold", "offset": 3, "length": 6},
                {"type": "italic", "offset": 3, "length": 6},
                {"type": "text_link", "offset": 12, "length": 6, "url": "https://example.com"},
            ],
        }
        self.message.body = json.dumps(post, ensure_ascii=False).encode()
        await on_message(self.message, self.bot, self.chats)
        sent = self.bot.send_message.await_args.kwargs
        self.assertEqual(sent["text"], post["text"])
        self.assertEqual([e.model_dump(exclude_none=True) for e in sent["entities"]], post["entities"])
        self.assertIsNone(sent["parse_mode"])
        self.assertTrue(sent["link_preview_options"].is_disabled)

    async def test_old_queue_messages_without_entities_still_send_without_preview(self):
        self.chats.add(-100)
        await on_message(self.message, self.bot, self.chats)
        sent = self.bot.send_message.await_args.kwargs
        self.assertEqual(sent["entities"], [])
        self.assertTrue(sent["link_preview_options"].is_disabled)

    async def test_invalid_entities_are_skipped(self):
        self.chats.add(-100)
        self.message.body = b'{"text":"hello", "entities":[{"type":"bold"}]}'
        await on_message(self.message, self.bot, self.chats)
        self.bot.send_message.assert_not_awaited()

    async def test_removed_chat_is_skipped_during_broadcast(self):
        self.chats.update({-100, -200})
        async def send(**kwargs):
            self.chats.clear()
        self.bot.send_message.side_effect = send
        await on_message(self.message, self.bot, self.chats)
        self.bot.send_message.assert_awaited_once()
