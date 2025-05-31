from dataclasses import dataclass


@dataclass
class ExampleData:
    example: str | None
    translation: str | None


@dataclass
class WordData:
    word: str | None
    transcription: str | None
    translation: str | None
    part_of_speech: str | None
    forms: str | None
    explanation: str | None
    examples: list[ExampleData] | None

    def create_message(self) -> str:
        message = (
            f'<b>{self.word or "Не указано"}</b>\n'
            f'<b>{self.transcription or "Не указана"}</b>\n'
            f'<b>{self.translation or "Не указан"}</b>\n'
            f'Часть речи: {self.part_of_speech or "Не указана"}\n'
            f'Формы: {self.forms or "Не указаны"}\n'
        )
        if self.examples:
            message += 'Примеры:\n'
            for example in self.examples:
                message += f'- {example.example} (перевод: {example.translation})\n'
        message += f'Объяснение: {self.explanation or "Не указано"}\n'
        return message
