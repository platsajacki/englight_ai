from typing import Any, Callable

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types.base import TelegramObject

from aiolimiter import AsyncLimiter

limiter = AsyncLimiter(20, 1)


class LimiterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Any],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        async with limiter:
            return await handler(event, data)
