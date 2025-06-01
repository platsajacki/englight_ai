from os import getenv
from typing import Literal

from httpx import Proxy

GEMINI_KEY = getenv('GEMINI_KEY')
if not GEMINI_KEY:
    raise ValueError('GEMINI_KEY environment variable is not set.')

DATABASE_URL = getenv('DATABASE_URL', 'sqlite+aiosqlite:///./database.db')
if not DATABASE_URL:
    raise ValueError('DATABASE_URL environment variable is not set.')

GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

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
        f'http://{PROXY_USERNAME}:{PROXY_PASSWORD}',
        auth=(PROXY_USERNAME, PROXY_PASSWORD),
    )


class PromptName:
    TRANSLATE = 'translate'


DEFAULT_TRANSLATE_PROMPT = 'Переведи слово или фразу на английском и пришли в фомите JSON:\n'
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
