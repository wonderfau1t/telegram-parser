from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.filters import (
    JOIN_TRANSITION,
    LEAVE_TRANSITION,
    ChatMemberUpdatedFilter,
    Command,
)
from aiogram.types import ChatMemberUpdated, Message

from config import Settings
from storage import save_chats

router = Router()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_bot_added(event: ChatMemberUpdated, bot: Bot, settings: Settings, chats: set[int]):
    if event.chat.type == ChatType.PRIVATE:
        return
    if event.from_user.id != settings.admin_id:
        chats.discard(event.chat.id)
        await bot.leave_chat(event.chat.id)
        save_chats(settings.chats_file, chats)
        return
    chats.add(event.chat.id)
    save_chats(settings.chats_file, chats)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def on_bot_removed(event: ChatMemberUpdated, chats: set[int], settings: Settings):
    chats.discard(event.chat.id)
    save_chats(settings.chats_file, chats)


@router.message(Command("register"))
async def register_chat(message: Message, settings: Settings, chats: set[int]):
    # Register an existing group; anonymous messages cannot identify the owner.
    if (
        message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}
        or not message.from_user
        or message.from_user.id != settings.admin_id
        or message.sender_chat
    ):
        return
    chats.add(message.chat.id)
    save_chats(settings.chats_file, chats)
    await message.answer("Чат подключён к рассылке.")
