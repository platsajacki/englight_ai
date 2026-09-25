from dataclasses import dataclass
from io import BytesIO

from aiogram.types import Message

from constants import DEFAULT_CHECK_SENTENCE_PROMPT, MAX_VOICE_SECONDS, OPENAI_CHECK_MODEL, PromptName
from core.data_types import SentenceCheck
from core.openai import OpenAIAnswer, request_openai, transcribe
from database.database import db
from database.managers import PromptManager, WordManager, WordProgressManager
from database.models import User, Word
from telegram.bot import bot


class SentenceError(Exception):
    """Проблема с ответом пользователя: текст исключения показывается ему, проверка продолжается."""


class SentenceSource:
    @staticmethod
    async def extract(message: Message) -> str:
        if message.text:
            return message.text.strip()
        if message.voice:
            return await SentenceSource.from_voice(message)
        raise SentenceError('Send a voice or text message with your sentence.')

    @staticmethod
    async def from_voice(message: Message) -> str:
        if message.voice is None or message.voice.duration > MAX_VOICE_SECONDS:
            raise SentenceError(f'Voice message is too long. Keep it under {MAX_VOICE_SECONDS} seconds.')
        audio = BytesIO()
        await bot.download(message.voice, destination=audio)
        sentence = await transcribe(audio.getvalue())
        if not sentence:
            raise SentenceError('Could not recognize your voice message. Try again.')
        return sentence


@dataclass
class SentenceChecker:
    word: Word
    sentence: str

    async def get_prompt(self) -> str:
        async with db.async_session() as session:
            template = await PromptManager(session).get_text_or_default(
                PromptName.CHECK_SENTENCE, DEFAULT_CHECK_SENTENCE_PROMPT
            )
        return template.format(
            word=self.word.word,
            part_of_speech=self.word.part_of_speech,
            translation=self.word.translation,
            sentence=self.sentence,
        )

    async def __call__(self) -> SentenceCheck | None:
        return await request_openai(
            await self.get_prompt(), SentenceCheck, OPENAI_CHECK_MODEL, reasoning={'effort': 'low'}
        )


@dataclass
class SentenceReview:
    user: User
    word_id: int

    async def check(self, sentence: str) -> OpenAIAnswer:
        word = await self.get_word()
        result = await SentenceChecker(word, sentence)()
        if result is None:
            raise SentenceError('Could not check your sentence. Try again.')
        async with db.async_session() as session:
            await WordProgressManager(session).record_review(self.user.id, self.word_id, result.is_correct)
        text = f'{result.create_message(sentence)}\n\n{word.to_message()}'
        return OpenAIAnswer(text=text, audio_text=result.corrected_sentence)

    async def get_word(self) -> Word:
        async with db.async_session() as session:
            word = await WordManager(session).get_with_examples(self.word_id)
        if word is None:
            raise SentenceError('Word not found. Press Cancel to stop the check.')
        return word
