from os import getenv
from typing import Literal

GEMINI_KEY = getenv('GEMINI_KEY')
if not GEMINI_KEY:
    raise ValueError('GEMINI_KEY environment variable is not set.')

DATABASE_URL = getenv('DATABASE_URL', 'sqlite+aiosqlite:///./database.db')
if not DATABASE_URL:
    raise ValueError('DATABASE_URL environment variable is not set.')

GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

NotProccesed = Literal['Не обработано']
NOT_PROCESSED: NotProccesed = 'Не обработано'


class PromptName:
    TRANSLATE = 'translate'


DEFAULT_TRANSLATE_PROMPT = getenv('DEFAULT_TRANSLATE_PROMPT', 'Переведи слово или фразу на английском')
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
