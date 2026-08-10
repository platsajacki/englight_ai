from dataclasses import dataclass

from httpx import AsyncClient
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)

from constants import DEFAULT_TRANSLATE_PROMPT, OPENAI_API_KEY, OPENAI_MODEL, PROXY_URL, PromptName
from core.data_types import TranslationResponse, WordData
from core.loggers import main_logger as logger
from database.database import db
from database.managers import PromptManager, WordManager
from utils import has_russian


@dataclass
class OpenAIAnswer:
    text: str
    audio_text: str | None = None


async def request_openai(prompt: str) -> TranslationResponse | None:
    async with AsyncClient(timeout=None, proxy=PROXY_URL) as http_client:
        async with AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client) as client:
            response = await client.responses.parse(
                model=OPENAI_MODEL,
                input=prompt,
                text_format=TranslationResponse,
            )
    logger.info('Request to OpenAI API successful with model: %s', OPENAI_MODEL)
    if response.output_parsed is None:
        logger.error(
            'OpenAI API response was not parsed. Status: %s, error: %s, output: %s',
            response.status,
            response.error,
            response.output,
        )
    return response.output_parsed


@dataclass
class OpenAIEnglight:
    message: str
    save_to_db: bool = True

    async def get_prompt(self) -> str:
        async with db.async_session() as session:
            prompt_manager = PromptManager(session)
            prompt = await prompt_manager.get_or_create_by_name(PromptName.TRANSLATE, DEFAULT_TRANSLATE_PROMPT)
            if not prompt.text:
                logger.error('Prompt text is empty for prompt name: %s', PromptName.TRANSLATE)
                return DEFAULT_TRANSLATE_PROMPT
            return prompt.text

    async def create_word_object(self, word_data: WordData) -> None:
        try:
            if not word_data.word:
                logger.error('Word is empty: %s', word_data)
                return
            if not word_data.part_of_speech:
                logger.error('Part of speech is empty: %s', word_data)
                return
            if has_russian(word_data.word):
                logger.error('Word contains Russian characters: %s', word_data.word)
                return
            async with db.async_session() as session:
                manager = WordManager(session)
                word = await manager.get_by_word_and_part_of_speech(word_data.word, word_data.part_of_speech)
                if word:
                    logger.info(
                        'Word object already exists for word: %s, part of speech: %s',
                        word_data.word,
                        word_data.part_of_speech,
                    )
                    return
                await manager.create_from_data(word_data)
        except Exception as e:
            logger.error('Error creating word object from WordData: %s\nError: %s', word_data, e)

    async def create_messages(self, words: list[WordData]) -> list[OpenAIAnswer]:
        messages = []
        for word_data in words:
            if self.save_to_db:
                logger.info('Creating WordData object for word: %s', word_data.word)
                await self.create_word_object(word_data)
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
            response = await request_openai(template.format(message=self.message))
            logger.info('Received response from OpenAI API: %s', response)
            return await self.process_answer(response)
        except AuthenticationError as e:
            logger.error('OpenAI API authentication failed: %s', e)
            return [OpenAIAnswer(text='OpenAI API key is invalid or does not have access to the selected model.')]
        except RateLimitError as e:
            logger.error('OpenAI API rate limit exceeded: %s', e)
            return [OpenAIAnswer(text='OpenAI API rate limit exceeded. Try again later.')]
        except APITimeoutError as e:
            logger.error('OpenAI API request timed out: %s', e)
            return [OpenAIAnswer(text='OpenAI API did not respond in time. Try again.')]
        except APIConnectionError as e:
            logger.error('Could not connect to OpenAI API: %s', e)
            return [OpenAIAnswer(text='Could not connect to OpenAI API. Try again later.')]
        except APIStatusError as e:
            logger.error('OpenAI API returned status %s: %s', e.status_code, e)
            return [OpenAIAnswer(text=f'OpenAI API returned an error with status {e.status_code}. Try again later.')]
        except OpenAIError as e:
            logger.error('OpenAI SDK error: %s', e)
            return [OpenAIAnswer(text='OpenAI API request failed. Try again later.')]
        except Exception as e:
            logger.error('Unexpected error while processing OpenAI response: %s', e, exc_info=True)
            return [OpenAIAnswer(text='Could not process the OpenAI response. Try again.')]
