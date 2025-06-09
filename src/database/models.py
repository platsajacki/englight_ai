from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableList
from constants import REPETITION_INTERVALS, UTC


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Prompt(Base):
    __tablename__ = 'prompts'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    text: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (UniqueConstraint('name', name='uq_prompt_name'),)


class Word(Base):
    __tablename__ = 'words'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[Optional[str]] = mapped_column(String(500), unique=True)
    transcription: Mapped[Optional[str]] = mapped_column(String(500))
    translation: Mapped[Optional[str]] = mapped_column(String(500))
    part_of_speech: Mapped[Optional[str]] = mapped_column(String(100))
    forms: Mapped[Optional[str]] = mapped_column(Text)
    explanation: Mapped[Optional[str]] = mapped_column(Text)

    examples: Mapped[List['Example']] = relationship(back_populates='word', cascade='all, delete-orphan')


class Example(Base):
    __tablename__ = 'examples'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    example: Mapped[Optional[str]] = mapped_column(Text)
    translation: Mapped[Optional[str]] = mapped_column(Text)

    word_id: Mapped[int] = mapped_column(ForeignKey('words.id', ondelete='CASCADE'))
    word: Mapped['Word'] = relationship(back_populates='examples')


class WordProgress(Base):
    __tablename__ = 'word_progress'

    id: Mapped[int] = mapped_column(primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey('words.id', ondelete='CASCADE'))
    review_history: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON),
        default=list,
        nullable=False,
    )

    word: Mapped['Word'] = relationship()

    @property
    def repetitions(self) -> int:
        return min(len(self.review_history), max(REPETITION_INTERVALS.keys()))

    @property
    def next_review(self) -> datetime:
        interval = REPETITION_INTERVALS[self.repetitions]
        if self.review_history:
            last_iso = self.review_history[-1]
            last = datetime.fromisoformat(last_iso)
        else:
            last = datetime.now(tz=UTC)
        return last + interval

    def record_review(self, success: bool) -> None:
        now_iso = datetime.now(tz=UTC).isoformat()
        if success:
            if len(self.review_history) < len(REPETITION_INTERVALS):
                self.review_history.append(now_iso)
            return
        self.review_history.clear()
        self.review_history.append(now_iso)
