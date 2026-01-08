import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable

from httpx import RequestError

from core.loggers import main_logger as logger


def retry_request(
    retries: int = 2, delay: int = 2, exceptions: tuple[type[BaseException]] = (RequestError,)
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Асинхронный декоратор для повторного вызова функции при возникновении ошибок.

    :param retries: количество попыток
    :param delay: задержка между попытками (в секундах)
    :param exceptions: кортеж исключений, при которых повторяется вызов
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f'Ошибка в функции "{func.__name__}": {e}\n'
                        f'Попытка {attempt} из {retries}. Жду {delay} секунд...'
                    )
                    await asyncio.sleep(delay)
            logger.error(
                f'Функция `{func.__name__}` не удалась после {retries} попыток. Последняя ошибка: {last_exception}'
            )
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
