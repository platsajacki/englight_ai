from typing import cast

from aiogram.filters import BaseFilter
from aiogram.types import Message

from constants import ALLOWED_CHATS


class AccessFilter(BaseFilter):
    def __init__(self, allowed_chats: set[str]) -> None:
        self.allowed_chats = allowed_chats

    async def __call__(self, message: Message) -> bool:
        allowed = (
            str(message.chat.id) in self.allowed_chats
            or message.from_user
            and str(message.from_user.id) in self.allowed_chats
        )
        if not allowed:
            await message.answer('Отказано в доступе.')
        return cast(bool, allowed)


access_filter = AccessFilter(allowed_chats=ALLOWED_CHATS)
