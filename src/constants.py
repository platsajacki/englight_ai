from datetime import time, timedelta
from os import getenv
from typing import Literal
from zoneinfo import ZoneInfo

from httpx import Proxy

UTC = ZoneInfo('UTC')
# 📚 Система интервальных повторений на основе принципов метода Leitner + SM2 (Anki)
# После 7 успешных повторений слово считается выученным и больше не показывается.
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

SCHEDULED_TIMES = [time(15, 30), time(20, 30)]

GEMINI_KEY = getenv('GEMINI_KEY')
if not GEMINI_KEY:
    raise ValueError('GEMINI_KEY environment variable is not set.')

DATABASE_URL = getenv('DATABASE_URL', 'sqlite+aiosqlite:///./database.db')
if not DATABASE_URL:
    raise ValueError('DATABASE_URL environment variable is not set.')

GEMINI_MODELS = ['gemini-2.0-flash-lite', 'gemini-2.0-flash']

NotProccesed = Literal['Не обработано']
NOT_PROCESSED: NotProccesed = 'Не обработано'

ADMIN_ID = getenv('ADMIN_ID', '0')
CHAT_ID = getenv('CHAT_ID', '0')
ALLOWED_CHATS_FROM_ENV = set(getenv('ALLOWED_CHATS', '').split(', '))
ALLOWED_CHATS_FOR_SAVING_TO_DB = {ADMIN_ID, CHAT_ID}
ALLOWED_CHATS = ALLOWED_CHATS_FOR_SAVING_TO_DB | ALLOWED_CHATS_FROM_ENV

USE_PROXY = bool(int(getenv('USE_PROXY', '0')))
PROXY_IP = getenv('PROXY_IP', '')
PROXY_PORT = getenv('PROXY_PORT', '')
PROXY_USERNAME = getenv('PROXY_USERNAME', '')
PROXY_PASSWORD = getenv('PROXY_PASSWORD', '')

PROXY = None
if USE_PROXY:
    if not (PROXY_IP and PROXY_PORT):
        raise ValueError('PROXY_IP and PROXY_PORT must be set when USE_PROXY is enabled.')
    PROXY = Proxy(
        f'http://{PROXY_IP}:{PROXY_PORT}',
        auth=(PROXY_USERNAME, PROXY_PASSWORD),
    )


class PromptName:
    TRANSLATE = 'translate'


DEFAULT_TRANSLATE_PROMPT = '''
1) Проанализируй сообщение:
{message}
2) Если это сообщение не является объяснением или переводом английского слова или фразы,
то строго ответь "Не обработано". Также, если в сообщении просьба не относится к переводу
или объяснению английского слова или фразы, ответь "Не обработано".
Ответ пришли в фомите JSON:\n'''
JSON_FORMAT = '''
{{
  "words": [
    {{
      "word": "слово или фраза на английском языке",
      "transcription": "транскрипция (в IPA)",
      "translation": "перевод на русский язык",
      "explanation": "объяснение на русском языке",
      "part_of_speech": "часть речи, например, 'noun'",
      "forms": "нумерованный список форм одной строкой с, см. выше",
      "examples": [
        {{
          "example": "пример на английском",
          "translation": "перевод примера"
        }}
      ]
    }}
  ]
}}'''
DEFAULT_TRANSLATE_PROMPT = DEFAULT_TRANSLATE_PROMPT + JSON_FORMAT
