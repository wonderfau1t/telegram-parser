import logging

from telethon.tl import types

logger = logging.getLogger(__name__)

ENTITY_TYPES = {
    types.MessageEntityMention: "mention",
    types.MessageEntityHashtag: "hashtag",
    types.MessageEntityCashtag: "cashtag",
    types.MessageEntityBotCommand: "bot_command",
    types.MessageEntityUrl: "url",
    types.MessageEntityEmail: "email",
    types.MessageEntityPhone: "phone_number",
    types.MessageEntityBold: "bold",
    types.MessageEntityItalic: "italic",
    types.MessageEntityUnderline: "underline",
    types.MessageEntityStrike: "strikethrough",
    types.MessageEntitySpoiler: "spoiler",
    types.MessageEntityCode: "code",
    types.MessageEntityPre: "pre",
    types.MessageEntityTextUrl: "text_link",
    types.MessageEntityMentionName: "text_link",
    types.MessageEntityBlockquote: "blockquote",
    types.MessageEntityCustomEmoji: "custom_emoji",
}


def serialize_entities(entities) -> list[dict]:
    result = []
    for entity in entities or []:
        kind = ENTITY_TYPES.get(type(entity))
        if kind is None:
            logger.warning("Пропущен неподдерживаемый тип оформления: %s", type(entity).__name__)
            continue
        # Both Telegram APIs use UTF-16 offsets: keep them unchanged, including emoji.
        item = {"type": kind, "offset": entity.offset, "length": entity.length}
        if isinstance(entity, types.MessageEntityTextUrl):
            item["url"] = entity.url
        elif isinstance(entity, types.MessageEntityMentionName):
            item["url"] = f"tg://user?id={entity.user_id}"
        elif isinstance(entity, types.MessageEntityPre):
            item["language"] = entity.language
        elif isinstance(entity, types.MessageEntityCustomEmoji):
            item["custom_emoji_id"] = str(entity.document_id)
        elif isinstance(entity, types.MessageEntityBlockquote) and entity.collapsed:
            item["type"] = "expandable_blockquote"
        result.append(item)
    return result
