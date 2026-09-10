import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telethon.tl import types

from src.formatting import serialize_entities
from src.messaging import on_latest_request, publish_message


class MessagingTests(unittest.IsolatedAsyncioTestCase):
    async def test_publishes_raw_text_and_nested_utf16_entities(self):
        message = types.Message(
            id=42, peer_id=types.PeerChannel(123), date=datetime.now(timezone.utc),
            message="😀 Жирный и ссылка <tag> *literal*",
            entities=[
                types.MessageEntityBold(3, 6), types.MessageEntityItalic(3, 6),
                types.MessageEntityTextUrl(12, 6, "https://example.com"),
            ],
        )
        self.assertNotEqual(message.text, message.raw_text)
        publish = AsyncMock()
        await publish_message(SimpleNamespace(default_exchange=SimpleNamespace(publish=publish)), "posts", message)
        body = json.loads(publish.await_args.args[0].body)
        self.assertEqual(body["text"], message.raw_text)
        self.assertEqual(body["entities"], [
            {"type": "bold", "offset": 3, "length": 6},
            {"type": "italic", "offset": 3, "length": 6},
            {"type": "text_link", "offset": 12, "length": 6, "url": "https://example.com"},
        ])
        self.assertEqual(body["chat_id"], -1000000000123)
        self.assertEqual(publish.await_args.kwargs["routing_key"], "posts")

    def test_special_formatting(self):
        entities = serialize_entities([
            types.MessageEntityUnderline(0, 2), types.MessageEntityStrike(0, 2),
            types.MessageEntitySpoiler(0, 2), types.MessageEntityCode(0, 2),
            types.MessageEntityPre(0, 2, "python"),
            types.MessageEntityBlockquote(0, 2),
            types.MessageEntityBlockquote(0, 2, collapsed=True),
            types.MessageEntityCustomEmoji(0, 2, document_id=1234567890123456789),
            types.MessageEntityMentionName(0, 2, user_id=123),
        ])
        self.assertEqual([e["type"] for e in entities], [
            "underline", "strikethrough", "spoiler", "code", "pre", "blockquote",
            "expandable_blockquote", "custom_emoji", "text_link",
        ])
        self.assertEqual(entities[4]["language"], "python")
        self.assertEqual(entities[7]["custom_emoji_id"], "1234567890123456789")
        self.assertEqual(entities[8]["url"], "tg://user?id=123")

    def test_plain_text_has_no_entities(self):
        self.assertEqual(serialize_entities(None), [])

    async def test_latest_request_publishes_one_post_with_formatting(self):
        post = types.Message(
            id=99, peer_id=types.PeerChannel(123), date=datetime.now(timezone.utc),
            message="Последний пост", entities=[types.MessageEntityBold(0, 9)],
        )
        client = SimpleNamespace(get_messages=AsyncMock(return_value=[post]))
        publish = AsyncMock()
        channel = SimpleNamespace(default_exchange=SimpleNamespace(publish=publish))
        context = AsyncMock()
        request = SimpleNamespace(process=MagicMock(return_value=context))
        await on_latest_request(request, client=client, chat="source", channel=channel, queue_name="posts")
        client.get_messages.assert_awaited_once_with("source", limit=1)
        publish.assert_awaited_once()
        body = json.loads(publish.await_args.args[0].body)
        self.assertEqual(body["message_id"], 99)
        self.assertEqual(body["text"], "Последний пост")
        self.assertEqual(body["entities"], [{"type": "bold", "offset": 0, "length": 9}])
        request.process.assert_called_once_with(requeue=True)
        self.assertIsNone(context.__aexit__.await_args.args[0])

    async def test_latest_request_in_empty_channel_is_acknowledged(self):
        client = SimpleNamespace(get_messages=AsyncMock(return_value=[]))
        context = AsyncMock()
        request = SimpleNamespace(process=MagicMock(return_value=context))
        with patch("src.messaging.publish_message", new_callable=AsyncMock) as publish:
            await on_latest_request(request, client=client, chat="source", channel=None, queue_name="posts")
            publish.assert_not_awaited()
        self.assertIsNone(context.__aexit__.await_args.args[0])

    async def test_latest_request_is_requeued_on_failure(self):
        client = SimpleNamespace(get_messages=AsyncMock(side_effect=OSError("offline")))
        context = AsyncMock()
        request = SimpleNamespace(process=MagicMock(return_value=context))
        with patch("src.messaging.asyncio.sleep", new_callable=AsyncMock):
            with self.assertRaises(OSError):
                await on_latest_request(request, client=client, chat="source", channel=None, queue_name="posts")
        request.process.assert_called_once_with(requeue=True)
        self.assertIs(context.__aexit__.await_args.args[0], OSError)
