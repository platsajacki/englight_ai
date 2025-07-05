from datetime import datetime
from typing import Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from constants import UTC
from core.data_types import WordData
from database.database import Database
from database.models import Example, Prompt, Word, WordProgress

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

    async def all(self) -> Sequence[T]:
        async with self.db.async_session() as session:
            result = await session.execute(select(self.model))
            return result.scalars().all()


class WordManager(Manager[Word]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, Word)

    async def get_by_word(self, word: str) -> Word | None:
        async with self.db.async_session() as session:
            result = await session.execute(select(self.model).where(func.lower(self.model.word) == word.lower()))
            return result.scalar_one_or_none()

    async def create_from_data(self, data: WordData) -> Word:
        async with self.db.async_session() as session:
            word = self.model(
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
            session.flush()
            word_progress = WordProgress(word_id=word.id)
            session.add(word_progress)
            await session.commit()
            await session.refresh(word)
            return word

    async def get_with_examples(self, word_id: int) -> Word | None:
        async with self.db.async_session() as session:
            result = await session.execute(
                select(self.model).where(self.model.id == word_id).options(selectinload(self.model.examples))
            )
            return result.scalar_one_or_none()

    async def get_all_with_examples(self) -> Sequence[Word]:
        async with self.db.async_session() as session:
            result = await session.execute(select(self.model).options(selectinload(self.model.examples)))
            return result.scalars().all()


class PromptManager(Manager[Prompt]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, Prompt)

    async def get_by_name(self, name: str) -> Prompt | None:
        async with self.db.async_session() as session:
            result = await session.execute(select(self.model).where(self.model.name == name))
            return result.scalar_one_or_none()

    async def get_or_create_by_name(self, name: str, prompt_text: str) -> Prompt:
        async with self.db.async_session() as session:
            result = await session.execute(select(self.model).where(self.model.name == name))
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            new_prompt = self.model(name=name, text=prompt_text)
            session.add(new_prompt)
            await session.commit()
            return new_prompt

    async def update_text_by_name(self, name: str, new_text: str) -> None:
        async with self.db.async_session() as session:
            result = await session.execute(select(self.model).where(self.model.name == name))
            prompt = result.scalar_one_or_none()
            if prompt:
                prompt.text = new_text
                await session.commit()


class WordProgressManager(Manager[WordProgress]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, WordProgress)

    async def get_next_review_words(self, limit: int = 10) -> Sequence[WordProgress]:
        now = datetime.now(tz=UTC)
        async with self.db.async_session() as session:
            results = await session.execute(
                select(self.model)
                .where(self.model.next_review_at <= now)
                .options(selectinload(self.model.word).selectinload(Word.examples))
                .order_by(self.model.next_review_at)
                .limit(limit)
            )
        return results.scalars().all()

    async def get_with_word(self, progress_id: int) -> WordProgress | None:
        async with self.db.async_session() as session:
            result = await session.execute(
                select(self.model).where(self.model.id == progress_id).options(selectinload(self.model.word))
            )
            return result.scalar_one_or_none()

    async def record_review(self, progress_id: int, success: bool) -> WordProgress | None:
        async with self.db.async_session() as session:
            wp = await self.get_with_word(progress_id)
            if wp:
                wp.record_review(success)
                await session.commit()
            return wp
