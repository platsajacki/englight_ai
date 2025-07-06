import asyncio
import re
from io import BytesIO

from gtts import gTTS


def has_russian(text: str) -> bool:
    return bool(re.search(r'[А-Яа-яЁё]', text))


def _text_to_speech_sync(text: str, lang: str = 'en') -> bytes:
    tts = gTTS(text, lang=lang)
    audio_file = BytesIO()
    tts.write_to_fp(audio_file)
    audio_file.seek(0)
    return audio_file.read()


async def text_to_speech(text: str, lang: str = 'en') -> bytes:
    loop = asyncio.get_event_loop()
    audio_bytes = await loop.run_in_executor(None, _text_to_speech_sync, text, lang)
    return audio_bytes
