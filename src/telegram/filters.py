from typing import cast

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from constants import ALLOWED_CHATS


class AccessFilter(BaseFilter):
    def __init__(self, allowed_chats: set[str]) -> None:
        self.allowed_chats = allowed_chats

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if isinstance(event, Message):
            chat_id = event.chat.id
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery) and event.message:
            chat_id = event.message.chat.id
            user_id = event.from_user.id if event.from_user else None
        else:
            return False
        allowed = str(chat_id) in self.allowed_chats or (user_id is not None and str(user_id) in self.allowed_chats)
        if not allowed:
            if isinstance(event, Message):
                await event.answer('Access denied.', show_alert=True)
            elif isinstance(event, CallbackQuery):
                await event.answer('Access denied.', show_alert=True)
        return cast(bool, allowed)


access_filter = AccessFilter(allowed_chats=ALLOWED_CHATS)
