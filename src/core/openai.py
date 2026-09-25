from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TypeVar

from httpx import AsyncClient
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    Omit,
    OpenAIError,
    RateLimitError,
    omit,
)
from openai.types.shared_params import Reasoning
from pydantic import BaseModel

from constants import (
    DEFAULT_TRANSLATE_PROMPT,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TRANSCRIBE_MODEL,
    PROXY_URL,
    PromptName,
)
from core.data_types import TranslationResponse, WordData
from core.loggers import app_logger as logger
from database.database import db
from database.managers import PromptManager, WordManager, WordProgressManager
from utils import has_russian

ResponseT = TypeVar('ResponseT', bound=BaseModel)

OPENAI_ERROR_MESSAGES: list[tuple[type[Exception], str]] = [
    (AuthenticationError, 'OpenAI API key is invalid or does not have access to the selected model.'),
    (RateLimitError, 'OpenAI API rate limit exceeded. Try again later.'),
    (APITimeoutError, 'OpenAI API did not respond in time. Try again.'),
    (APIConnectionError, 'Could not connect to OpenAI API. Try again later.'),
    (APIStatusError, 'OpenAI API returned an error with status {status_code}. Try again later.'),
    (OpenAIError, 'OpenAI API request failed. Try again later.'),
]


@dataclass
class OpenAIAnswer:
    text: str
    audio_text: str | None = None


def describe_openai_error(error: Exception) -> str:
    logger.error('OpenAI request failed: %s', error, exc_info=True)
    for error_type, text in OPENAI_ERROR_MESSAGES:
        if isinstance(error, error_type):
            return text.format(status_code=getattr(error, 'status_code', None))
    return 'Could not process the OpenAI response. Try again.'


@asynccontextmanager
async def openai_client() -> AsyncGenerator[AsyncOpenAI]:
    async with AsyncClient(timeout=None, proxy=PROXY_URL) as http_client:
        async with AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client) as client:
            yield client


async def request_openai(
    prompt: str, text_format: type[ResponseT], model: str, reasoning: Reasoning | Omit = omit
) -> ResponseT | None:
    async with openai_client() as client:
        response = await client.responses.parse(model=model, input=prompt, text_format=text_format, reasoning=reasoning)
    logger.info('Request to OpenAI API successful with model: %s', model)
    if response.output_parsed is None:
        logger.error(
            'OpenAI API response was not parsed. Status: %s, error: %s, output: %s',
            response.status,
            response.error,
            response.output,
        )
    return response.output_parsed


async def transcribe(audio: bytes) -> str:
    async with openai_client() as client:
        transcription = await client.audio.transcriptions.create(
            model=OPENAI_TRANSCRIBE_MODEL, file=('voice.ogg', audio), language='en'
        )
    logger.info('Transcribed voice with model %s: %s', OPENAI_TRANSCRIBE_MODEL, transcription.text)
    return transcription.text.strip()


@dataclass
class OpenAIEnglight:
    message: str
    user_id: int | None = None

    async def get_prompt(self) -> str:
        async with db.async_session() as session:
            return await PromptManager(session).get_text_or_default(PromptName.TRANSLATE, DEFAULT_TRANSLATE_PROMPT)

    @staticmethod
    def is_valid(word_data: WordData) -> bool:
        if not word_data.word:
            logger.error('Word is empty: %s', word_data)
            return False
        if not word_data.part_of_speech:
            logger.error('Part of speech is empty: %s', word_data)
            return False
        if has_russian(word_data.word):
            logger.error('Word contains Russian characters: %s', word_data.word)
            return False
        return True

    async def save_for_user(self, word_data: WordData, user_id: int) -> None:
        try:
            if not self.is_valid(word_data):
                return
            async with db.async_session() as session:
                word = await WordManager(session).get_or_create_from_data(word_data)
                await WordProgressManager(session).add_for_user(user_id, word.id)
        except Exception as e:
            logger.error('Error saving word for user %s from WordData: %s\nError: %s', user_id, word_data, e)

    async def create_messages(self, words: list[WordData]) -> list[OpenAIAnswer]:
        messages = []
        for word_data in words:
            if self.user_id is not None:
                logger.info('Saving word "%s" for user %s', word_data.word, self.user_id)
                await self.save_for_user(word_data, self.user_id)
            messages.append(OpenAIAnswer(text=word_data.create_message(), audio_text=word_data.word))
        return messages

    async def process_answer(self, answer: TranslationResponse | None) -> list[OpenAIAnswer]:
        if answer is None:
            return [OpenAIAnswer(text='OpenAI API returned an invalid response format. Try again.')]
        if not answer.words:
            return [OpenAIAnswer(text='OpenAI API returned "not processed" response. Try again.')]
        return await self.create_messages(answer.words)

    async def __call__(self) -> list[OpenAIAnswer]:
        try:
            logger.info('Requesting OpenAI API with message: %s', self.message)
            template = await self.get_prompt()
            response = await request_openai(template.format(message=self.message), TranslationResponse, OPENAI_MODEL)
            logger.info('Received response from OpenAI API: %s', response)
            return await self.process_answer(response)
        except Exception as e:
            return [OpenAIAnswer(text=describe_openai_error(e))]
