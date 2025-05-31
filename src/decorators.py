import time
from functools import wraps
from logging import getLogger
from typing import Any, Callable

import requests

logger = getLogger(__name__)


def retry_request(
    retries: int = 2, delay: int = 2, exceptions: tuple[type[BaseException]] = (requests.RequestException,)
) -> Callable:
    """
    Декоратор, повторяющий вызов функции при возникновении указанных исключений.

    :param retries: число попыток (по умолчанию 2)
    :param delay: время задержки между попытками (по умолчанию 1 секунды)
    :param exceptions: кортеж исключений, при возникновении которых будет выполняться повторный вызов
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            last_exception = None
            for attempt in range(1, retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.error(
                        f'Ошибка в функции "{func.__name__}": {e}.\n'
                        f'Попытка {attempt} из {retries}. Ожидание {delay} секунд.'
                    )
                    time.sleep(delay)
            logger.error(
                f'Функция `{func.__name__}` не удалась после {retries} попыток. Последняя ошибка: {last_exception}'
            )
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
