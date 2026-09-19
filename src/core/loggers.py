from logging import getLogger
from logging.config import dictConfig

app_logger = getLogger('app')


def get_logging_dict(log_formatter: str, datetime_formatter: str) -> dict:
    return {
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
        },
        'loggers': {
            'app': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }


LOG_FORMATTER = (
    '[%(asctime)s] [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d\nFile: %(pathname)s\nMessage: %(message)s\n'
)
DATETIME_FORMATTER = '%d.%m.%Y %H:%M:%S'


def setup_logging() -> None:
    dictConfig(get_logging_dict(log_formatter=LOG_FORMATTER, datetime_formatter=DATETIME_FORMATTER))
