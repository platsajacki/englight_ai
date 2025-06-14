import json
import random
from dataclasses import dataclass
from logging import getLogger

from httpx import AsyncClient, RequestError

from constants import (
    DEFAULT_TRANSLATE_PROMPT,
    GEMINI_KEY,
    GEMINI_MODELS,
    NOT_PROCESSED,
    PROXY,
    NotProccesed,
    PromptName,
)
from core.data_types import ExampleData, WordData
from core.decorators import retry_request
from database.database import db
from database.managers import PromptManager, WordManager

logger = getLogger(__name__)


@retry_request()
async def request_gemini(prompt: str) -> dict | NotProccesed:
    headers = {'Content-Type': 'application/json'}
    params = {'key': GEMINI_KEY}
    data = {'contents': [{'parts': [{'text': prompt}]}]}
    async with AsyncClient(timeout=30.0, proxy=PROXY) as client:
        model = random.choice(GEMINI_MODELS)
        logger.info(f'Request to Gemini API successful with model: {model}')
        base_url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        response = await client.post(base_url, headers=headers, json=data, params=params)
        response.raise_for_status()
        return response.json()


@dataclass
class GeminiEnglight:
    message: str
    save_to_db: bool = True

    async def get_prompt(self) -> str:
        prompt_manager = PromptManager(db)
        prompt = await prompt_manager.get_or_create_by_name(PromptName.TRANSLATE, DEFAULT_TRANSLATE_PROMPT)
        if not prompt.text:
            logger.error('Prompt text is empty for prompt name: %s', PromptName.TRANSLATE)
            return DEFAULT_TRANSLATE_PROMPT
        return prompt.text

    def extract_words(self, answer: dict) -> str | NotProccesed:
        cleared_answer = (
            answer.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Не обработано')
        )
        if cleared_answer == NOT_PROCESSED:
            return NOT_PROCESSED
        json_string = cleared_answer.replace('```', '')
        if json_string.startswith('json'):
            json_string = json_string[4:].strip()
        return json_string

    def parse_json(self, json_string: str) -> dict | NotProccesed:
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            logger.error('JSON decoding error: %s', json_string)
            return NOT_PROCESSED

    async def create_word_object(self, word_data: WordData) -> None:
        try:
            if not isinstance(word_data, WordData) or not word_data.word:
                logger.error('Invalid WordData object: %s', word_data)
                return
            manager = WordManager(db)
            word = await manager.get_by_word(word_data.word)
            if word:
                logger.info('Word object already exists for word: %s', word_data.word)
                return
            await manager.create_from_data(word_data)
        except Exception as e:
            logger.error('Error creating word object from WordData: %s\nError: %s', word_data, e)

    async def create_messages(self, words: list) -> list[str]:
        messages = []
        for word in words:
            if not isinstance(word, dict):
                msg = 'Expected a dictionary for word, got: %s, value %s' % (type(word), word)
                logger.error(msg)
                messages.append(msg)
            try:
                examples = word.pop('examples', [])
                example_objects = [ExampleData(**example) for example in examples]
                word_data = WordData(examples=example_objects, **word)
                if self.save_to_db:
                    logger.info('Creating WordData object for word: %s', word_data.word)
                    await self.create_word_object(word_data)
            except TypeError as e:
                msg = 'Error creating WordData from word: %s\nError: %s' % (str(word), str(e))
                logger.error(msg)
                messages.append(msg)
            messages.append(word_data.create_message())
        return messages

    async def process_answer(self, answer: dict) -> dict | list:
        cleared_answer = self.extract_words(answer)
        if cleared_answer == NOT_PROCESSED:
            return ['Gemini API returned "not processed" response. Try again.']
        words = self.parse_json(cleared_answer)
        if not isinstance(words, dict):
            return ['Gemini API returned an invalid response format. Try again.']
        words_list = words.get('words', [])
        return await self.create_messages(words_list) if words_list else []

    async def __call__(self) -> dict | list[NotProccesed | str]:
        try:
            logger.info('Requesting Gemini API with message: %s', self.message)
            template = await self.get_prompt()
            prompt = template.format(message=self.message)
            response = await request_gemini(prompt)
            logger.info('Received response from Gemini API: %s', response)
            answers = await self.process_answer(response)
            return answers
        except RequestError as e:
            logger.error('Request to Gemini API failed:\n%s', str(e))
            return ['Oops, something went wrong with Gemini API request. Try again.']
        except Exception as e:
            logger.error('An unexpected error occurred:\n%s', str(e), exc_info=True)
            return ['Oops, something went wrong. Try again.']
