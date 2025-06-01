from typing import Generic, TypeVar

from sqlalchemy import select

from core.data_types import WordData
from database.database import Database
from database.models import Example, Prompt, Word

T = TypeVar('T')


class Manager(Generic[T]):
    def __init__(self, db: Database, model: type[T]) -> None:
        self.db = db
        self.model = model

    async def get(self, obj_id: int) -> T | None:
        async with self.db.async_session() as session:
            return await session.get(self.model, obj_id)

    async def save(self, obj: T) -> None:
        async with self.db.async_session() as session:
            session.add(obj)
            await session.commit()

    async def delete(self, obj_id: int) -> None:
        async with self.db.async_session() as session:
            obj = await session.get(self.model, obj_id)
            if obj:
                await session.delete(obj)
                await session.commit()


class WordManager(Manager[Word]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, Word)

    async def get_by_word(self, word: str) -> Word | None:
        async with self.db.async_session() as session:
            result = await session.execute(select(Word).where(Word.word == word))
            return result.scalar_one_or_none()

    async def create_from_data(self, data: WordData) -> Word:
        async with self.db.async_session() as session:
            word = Word(
                word=data.word,
                transcription=data.transcription,
                translation=data.translation,
                part_of_speech=data.part_of_speech,
                forms=data.forms,
                explanation=data.explanation,
            )
            if data.examples:
                for example_data in data.examples:
                    example = Example(
                        example=example_data.example,
                        translation=example_data.translation,
                        word=word,
                    )
                    word.examples.append(example)
            session.add(word)
            await session.commit()
            await session.refresh(word)
            return word


class PromptManager(Manager[Prompt]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, Prompt)

    async def get_by_name(self, name: str) -> Prompt | None:
        async with self.db.async_session() as session:
            result = await session.execute(select(Prompt).where(Prompt.name == name))
            return result.scalar_one_or_none()

    async def get_or_create_by_name(self, name: str, prompt_text: str) -> Prompt:
        async with self.db.async_session() as session:
            result = await session.execute(select(Prompt).where(Prompt.name == name))
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            new_prompt = Prompt(name=name, text=prompt_text)
            session.add(new_prompt)
            await session.commit()
            return new_prompt

    async def update_text_by_name(self, name: str, new_text: str) -> None:
        async with self.db.async_session() as session:
            result = await session.execute(select(Prompt).where(Prompt.name == name))
            prompt = result.scalar_one_or_none()
            if prompt:
                prompt.text = new_text
                await session.commit()
