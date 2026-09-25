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
LEARNED_LEVEL = len(REPETITION_INTERVALS)

SCHEDULED_TIMES = [time(7, 30), time(12, 30)]

OPENAI_API_KEY = getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError('OPENAI_API_KEY environment variable is not set.')
OPENAI_MODEL = getenv('OPENAI_MODEL', 'gpt-5-nano')
OPENAI_CHECK_MODEL = getenv('OPENAI_CHECK_MODEL', 'gpt-5-mini')
OPENAI_TRANSCRIBE_MODEL = getenv('OPENAI_TRANSCRIBE_MODEL', 'gpt-4o-mini-transcribe')
MAX_VOICE_SECONDS = 60

DATABASE_URL = getenv('DATABASE_URL', 'sqlite+aiosqlite:///./database.db')
if not DATABASE_URL:
    raise ValueError('DATABASE_URL environment variable is not set.')

ADMIN_ID = getenv('ADMIN_ID', '0')
CHAT_ID = getenv('CHAT_ID', '0')
ALLOWED_CHATS_FROM_ENV = {chat.strip() for chat in getenv('ALLOWED_CHATS', '').split(',') if chat.strip()}
ALLOWED_CHATS = {ADMIN_ID, CHAT_ID} | ALLOWED_CHATS_FROM_ENV
WORD_PER_TIME = 5
PROXY_URL = getenv('PROXY_URL')


class PromptName:
    TRANSLATE = 'translate'
    CHECK_SENTENCE = 'check_sentence'


DEFAULT_TRANSLATE_PROMPT = '''
Проанализируй сообщение:
{message}
Если сообщение не является объяснением или переводом английского слова или фразы,
не извлекай из него слова. Также не извлекай слова, если просьба не относится к переводу
или объяснению английского слова или фразы.
'''

DEFAULT_CHECK_SENTENCE_PROMPT = '''
Ученик изучает английское слово и составил с ним предложение.
Слово: {word}
Часть речи: {part_of_speech}
Перевод: {translation}
Предложение ученика: {sentence}

Предложение может быть распознано из голосового сообщения, поэтому игнорируй пунктуацию и регистр букв.
Считай предложение верным, только если слово использовано в указанном значении и части речи,
а само предложение грамматически правильное и звучит естественно.
В corrected_sentence дай исправленный вариант предложения на английском языке,
если ошибок нет, повтори предложение ученика.
В feedback кратко объясни ошибки на русском языке, исправления и примеры приводи на английском.
Если ошибок нет, коротко похвали и при необходимости предложи более естественный вариант.
'''

PROMPT_PLACEHOLDERS = {
    PromptName.TRANSLATE: ['{message}'],
    PromptName.CHECK_SENTENCE: ['{word}', '{part_of_speech}', '{translation}', '{sentence}'],
}
