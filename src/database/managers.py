from datetime import datetime
from typing import Generic, Optional, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from constants import UTC
from core.data_types import WordData
from database.models import Example, Prompt, Word, WordProgress

T = TypeVar('T')


class Manager(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def get(self, obj_id: int) -> Optional[T]:
        return await self.session.get(self.model, obj_id)

    async def save(self, obj: T) -> None:
        self.session.add(obj)
        await self.session.commit()

    async def delete(self, obj_id: int) -> None:
        obj = await self.session.get(self.model, obj_id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()

    async def all(self) -> Sequence[T]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()


class WordManager(Manager[Word]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Word)

    async def get_by_word(self, word: str) -> Optional[Word]:
        result = await self.session.execute(select(self.model).where(func.lower(self.model.word) == word.lower()))
        return result.scalar_one_or_none()

    async def create_from_data(self, data: WordData) -> Word:
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
        self.session.add(word)
        await self.session.flush()
        word_progress = WordProgress(word_id=word.id)
        self.session.add(word_progress)
        await self.session.commit()
        await self.session.refresh(word)
        return word

    async def get_with_examples(self, word_id: int) -> Optional[Word]:
        result = await self.session.execute(
            select(self.model).where(self.model.id == word_id).options(selectinload(self.model.examples))
        )
        return result.scalar_one_or_none()

    async def get_all_with_examples(self) -> Sequence[Word]:
        result = await self.session.execute(select(self.model).options(selectinload(self.model.examples)))
        return result.scalars().all()


class PromptManager(Manager[Prompt]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Prompt)

    async def get_by_name(self, name: str) -> Optional[Prompt]:
        result = await self.session.execute(select(self.model).where(self.model.name == name))
        return result.scalar_one_or_none()

    async def get_or_create_by_name(self, name: str, prompt_text: str) -> Prompt:
        result = await self.session.execute(select(self.model).where(self.model.name == name))
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        new_prompt = self.model(name=name, text=prompt_text)
        self.session.add(new_prompt)
        await self.session.commit()
        return new_prompt

    async def update_text_by_name(self, name: str, new_text: str) -> None:
        result = await self.session.execute(select(self.model).where(self.model.name == name))
        prompt = result.scalar_one_or_none()
        if prompt:
            prompt.text = new_text
            await self.session.commit()


class WordProgressManager(Manager[WordProgress]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WordProgress)

    async def get_next_review_words(self, limit: int = 10) -> Sequence[WordProgress]:
        now = datetime.now(tz=UTC)
        results = await self.session.execute(
            select(self.model)
            .where(self.model.next_review_at <= now)
            .options(selectinload(self.model.word).selectinload(Word.examples))
            .order_by(self.model.next_review_at)
            .limit(limit)
        )
        return results.scalars().all()

    async def get_with_word(self, progress_id: int) -> Optional[WordProgress]:
        result = await self.session.execute(
            select(self.model).where(self.model.id == progress_id).options(selectinload(self.model.word))
        )
        return result.scalar_one_or_none()

    async def record_review(self, progress_id: int, success: bool) -> Optional[WordProgress]:
        wp = await self.get_with_word(progress_id)
        if wp:
            wp.record_review(success)
            await self.session.commit()
            await self.session.refresh(wp)
        return wp
