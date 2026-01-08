from logging import getLogger
from logging.config import dictConfig
from os import getenv
from typing import Any

main_logger = getLogger('main')

LOKI_CONTAINER = getenv('LOKI_CONTAINER', 'loki.loki.svc.cluster.local:3100')


def get_logging_dict(
    log_formatter: str,
    datetime_formatter: str,
    loki_container: str,
    loki_app_name: str,
    debug: bool | int = False,
) -> dict:
    cfg: dict[str, Any] = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'main': {
                'format': log_formatter,
                'datefmt': datetime_formatter,
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'main',
            },
            'loki': {
                'level': 'DEBUG',
                'class': 'logging_loki.LokiQueueHandler',
                'url': f'http://{loki_container}/loki/api/v1/push',
                'tags': {'application': loki_app_name},
                'version': '1',
            },
        },
        'loggers': {
            'main': {
                'handlers': ['console', 'loki'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    if debug:
        cfg['loggers']['main']['handlers'].remove('loki')
    return cfg


LOG_FORMATTER = (
    '[%(asctime)s] [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d\nFile: %(pathname)s\nMessage: %(message)s\n'
)
DATETIME_FORMATTER = '%d.%m.%Y %H:%M:%S'
LOKI_APP_NAME = getenv('LOKI_APP_NAME', 'englight_ai')
LOCAL = bool(int(getenv('LOCAL', '0')))


def setup_logging() -> None:
    cfg = get_logging_dict(
        log_formatter=LOG_FORMATTER,
        datetime_formatter=DATETIME_FORMATTER,
        loki_container=LOKI_CONTAINER,
        loki_app_name=LOKI_APP_NAME,
        debug=LOCAL,
    )
    dictConfig(cfg)
