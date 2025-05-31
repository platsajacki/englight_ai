import json
from dataclasses import dataclass
from logging import getLogger

import requests

from constants import GEMINI_BASE_URL, GEMINI_KEY, NOT_PROCESSED, PROMPT, NotProccesed
from data_types import ExampleData, WordData
from decorators import retry_request

logger = getLogger(__name__)


@retry_request()
def request_gemini(prompt: str) -> dict | NotProccesed:
    headers = {'Content-Type': 'application/json'}
    data = {
        'contents': [{'parts': [{'text': prompt}]}],
    }
    params = {'key': GEMINI_KEY}
    response = requests.post(GEMINI_BASE_URL, headers=headers, json=data, params=params)
    response.raise_for_status()
    return response.json()


@dataclass
class GeminiEnglight:
    message: str
    PROMPT: str = PROMPT

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

    def create_messages(self, words: list) -> list[str]:
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
            except TypeError as e:
                msg = 'Error creating WordData from word: %s\nError: %s' % (str(word), str(e))
                logger.error(msg)
                messages.append(msg)
            messages.append(word_data.create_message())
        return messages

    def process_answer(self, answer: dict) -> dict | list:
        cleared_answer = self.extract_words(answer)
        if cleared_answer == NOT_PROCESSED:
            return []
        words = self.parse_json(cleared_answer)
        if not isinstance(words, dict):
            return []
        words_list = words.get('words', [])
        return self.create_messages(words_list) if words_list else []

    def __call__(self) -> dict | list[NotProccesed]:
        try:
            logger.info('Requesting Gemini API with message: %s', self.message)
            prompt = self.PROMPT.format(message=self.message)
            response = request_gemini(prompt)
            return self.process_answer(response)
        except requests.RequestException as e:
            logger.error('Request to Gemini API failed:\n%s', e)
            return []
        except Exception as e:
            logger.error('An unexpected error occurred:\n%s', e, exc_info=True)
            return []
