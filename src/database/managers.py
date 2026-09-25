from datetime import datetime
from typing import Generic, Iterable, Optional, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from constants import UTC
from core.data_types import WordData
from database.models import Example, Prompt, User, Word, WordProgress

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


class UserManager(Manager[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_or_create(self, telegram_id: int, full_name: str) -> User:
        result = await self.session.execute(select(self.model).where(self.model.telegram_id == telegram_id))
        user = result.scalar_one_or_none() or self.model(telegram_id=telegram_id)
        if user.id is None or user.full_name != full_name:
            user.full_name = full_name
            await self.save(user)
        return user

    async def get_by_telegram_ids(self, telegram_ids: Iterable[int]) -> Sequence[User]:
        result = await self.session.execute(select(self.model).where(self.model.telegram_id.in_(list(telegram_ids))))
        return result.scalars().all()


class WordManager(Manager[Word]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Word)

    async def get_by_word_and_part_of_speech(self, word: str, part_of_speech: str) -> Optional[Word]:
        result = await self.session.execute(
            select(self.model).where(
                func.lower(self.model.word) == word.lower(),
                func.lower(self.model.part_of_speech) == part_of_speech.lower(),
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_from_data(self, data: WordData) -> Word:
        word = await self.get_by_word_and_part_of_speech(data.word or '', data.part_of_speech or '')
        return word or await self.create_from_data(data)

    async def create_from_data(self, data: WordData) -> Word:
        word = self.model(
            word=data.word,
            transcription=data.transcription,
            translation=data.translation,
            part_of_speech=data.part_of_speech,
            forms=data.forms,
            explanation=data.explanation,
            examples=[Example(example=ex.example, translation=ex.translation) for ex in data.examples],
        )
        await self.save(word)
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

    async def add_for_user(self, user_id: int, word_id: int) -> None:
        if await self.get_for_user_and_word(user_id, word_id):
            return
        await self.save(self.model(user_id=user_id, word_id=word_id))

    async def get_next_review_words(self, user_id: int, limit: int = 10) -> Sequence[WordProgress]:
        now = datetime.now(tz=UTC)
        results = await self.session.execute(
            select(self.model)
            .where(self.model.user_id == user_id, self.model.next_review_at <= now)
            .options(selectinload(self.model.word).selectinload(Word.examples))
            .order_by(self.model.next_review_at)
            .limit(limit)
        )
        return results.scalars().all()

    async def get_for_user_and_word(self, user_id: int, word_id: int) -> Optional[WordProgress]:
        result = await self.session.execute(
            select(self.model)
            .where(self.model.user_id == user_id, self.model.word_id == word_id)
            .options(selectinload(self.model.word))
        )
        return result.scalar_one_or_none()

    async def all_for_user(self, user_id: int) -> Sequence[WordProgress]:
        result = await self.session.execute(select(self.model).where(self.model.user_id == user_id))
        return result.scalars().all()

    async def find_for_user_by_word(self, user_id: int, word: str) -> Sequence[WordProgress]:
        result = await self.session.execute(
            select(self.model)
            .join(self.model.word)
            .where(self.model.user_id == user_id, func.lower(Word.word) == word.lower())
            .options(selectinload(self.model.word))
        )
        return result.scalars().all()

    async def record_review(self, user_id: int, word_id: int, success: bool) -> Optional[WordProgress]:
        wp = await self.get_for_user_and_word(user_id, word_id)
        if wp:
            wp.record_review(success)
            await self.session.commit()
        return wp

    async def delete_for_user(self, user_id: int, word_id: int) -> Optional[WordProgress]:
        wp = await self.get_for_user_and_word(user_id, word_id)
        if wp:
            await self.session.delete(wp)
            await self.session.commit()
        return wp
