from typing import List, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
