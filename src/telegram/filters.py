from typing import Optional, cast

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from constants import ADMIN_ID, ALLOWED_CHATS
from database.models import User


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


class AdminFilter(BaseFilter):
    def __init__(self, admin_id: str) -> None:
        self.admin_id = admin_id

    async def __call__(self, message: Message) -> bool:
        is_admin = message.from_user is not None and str(message.from_user.id) == self.admin_id
        if not is_admin:
            await message.answer('Access denied.')
        return is_admin


class PrivateUserFilter(BaseFilter):
    """Пропускает только зарегистрированных пользователей в личном чате (см. UserMiddleware)."""

    async def __call__(self, event: Message | CallbackQuery, user: Optional[User]) -> bool:
        if user is None:
            await event.answer('Use this command in a private chat.')
        return user is not None


access_filter = AccessFilter(allowed_chats=ALLOWED_CHATS)
private_user_filter = PrivateUserFilter()
admin_filter = AdminFilter(admin_id=ADMIN_ID)
