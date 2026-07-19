from datetime import time, timedelta
from os import getenv
from zoneinfo import ZoneInfo

UTC = ZoneInfo('UTC')
# 📚 Система интервальных повторений на основе принципов метода Leitner + SM2 (Anki)
# После 7 успешных повторений слово считается выученным.
# 8 уровень означает, что слово выучено и не будет показано в будущем.
REPETITION_INTERVALS = {
    0: timedelta(days=1),
    1: timedelta(days=2),
    2: timedelta(days=3),
    3: timedelta(days=7),
    4: timedelta(days=14),
    5: timedelta(days=30),
    6: timedelta(days=60),
    7: timedelta(days=120),
}

SCHEDULED_TIMES = [time(7, 30), time(12, 30)]

OPENAI_API_KEY = getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError('OPENAI_API_KEY environment variable is not set.')
OPENAI_MODEL = getenv('OPENAI_MODEL', 'gpt-5-nano')

DATABASE_URL = getenv('DATABASE_URL', 'sqlite+aiosqlite:///./database.db')
if not DATABASE_URL:
    raise ValueError('DATABASE_URL environment variable is not set.')

ADMIN_ID = getenv('ADMIN_ID', '0')
CHAT_ID = getenv('CHAT_ID', '0')
ALLOWED_CHATS_FROM_ENV = set(getenv('ALLOWED_CHATS', '').split(', '))
ALLOWED_CHATS_FOR_SAVING_TO_DB = {ADMIN_ID, CHAT_ID}
ALLOWED_CHATS = ALLOWED_CHATS_FOR_SAVING_TO_DB | ALLOWED_CHATS_FROM_ENV

PROXY_URL = getenv('PROXY_URL')


class PromptName:
    TRANSLATE = 'translate'


DEFAULT_TRANSLATE_PROMPT = '''
Проанализируй сообщение:
{message}
Если сообщение не является объяснением или переводом английского слова или фразы,
не извлекай из него слова. Также не извлекай слова, если просьба не относится к переводу
или объяснению английского слова или фразы.
'''
