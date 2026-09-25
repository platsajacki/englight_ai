from typing import Any, Callable, Optional

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Message
from aiogram.types.base import TelegramObject

from constants import ALLOWED_CHATS
from database.database import db
from database.managers import UserManager
from database.models import User


class UserMiddleware(BaseMiddleware):
    """Регистрирует пользователя из ALLOWED_CHATS и передаёт его в хендлер как `user`.

    В группах и для незарегистрируемых отправителей `user` равен None: бот только переводит.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Any],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        data['user'] = await self.get_user(event)
        return await handler(event, data)

    async def get_user(self, event: TelegramObject) -> Optional[User]:
        if not self.is_private_allowed(event):
            return None
        tg_user = event.from_user  # type: ignore[attr-defined]
        async with db.async_session() as session:
            return await UserManager(session).get_or_create(tg_user.id, tg_user.full_name)

    @staticmethod
    def is_private_allowed(event: TelegramObject) -> bool:
        message = event.message if isinstance(event, CallbackQuery) else event
        if not isinstance(message, Message) or message.chat.type != ChatType.PRIVATE:
            return False
        from_user = getattr(event, 'from_user', None)
        return from_user is not None and str(from_user.id) in ALLOWED_CHATS
