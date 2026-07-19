from pydantic import BaseModel, Field


class ExampleData(BaseModel):
    example: str | None = Field(description='Пример использования на английском языке')
    translation: str | None = Field(description='Перевод примера на русский язык')


class WordData(BaseModel):
    word: str | None = Field(description='Слово или фраза на английском языке')
    transcription: str | None = Field(description='Транскрипция в IPA')
    translation: str | None = Field(description='Перевод на русский язык')
    part_of_speech: str | None = Field(description='Часть речи на английском языке, например noun')
    forms: str | None = Field(description='Нумерованный список форм слова одной строкой')
    explanation: str | None = Field(description='Объяснение на русском языке')
    examples: list[ExampleData] = Field(description='Примеры использования слова или фразы')

    def create_message(self) -> str:
        message = (
            f'<b>{self.word or "Не указано"}</b>\n'
            f'<b>{self.transcription or "Не указана"}</b>\n'
            f'<b>{self.translation or "Не указан"}</b>\n'
            f'Часть речи: {self.part_of_speech or "Не указана"}\n'
            f'Формы:\n{self.forms or "Не указаны"}\n'
        )
        if self.examples:
            message += 'Примеры:\n'
            for example in self.examples:
                message += f'- {example.example} (перевод: {example.translation})\n'
        message += f'Объяснение:\n{self.explanation or "Не указано"}\n'
        return message


class TranslationResponse(BaseModel):
    words: list[WordData] = Field(
        description='Найденные английские слова и фразы; пустой список для нерелевантного сообщения'
    )
