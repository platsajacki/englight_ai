from typing import Optional

from sqlalchemy import select

from database.database import Database
from database.models import Prompt


class PromptManager:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get(self, prompt_id: int) -> Optional[Prompt]:
        async with self.db.async_session() as session:
            return await session.get(Prompt, prompt_id)

    async def save(self, prompt: Prompt) -> None:
        async with self.db.async_session() as session:
            session.add(prompt)
            await session.commit()

    async def delete(self, prompt_id: int) -> None:
        async with self.db.async_session() as session:
            prompt = await self.get(prompt_id)
            if prompt:
                await session.delete(prompt)
                await session.commit()

    async def update_text_by_name(self, name: str, new_text: str) -> None:
        async with self.db.async_session() as session:
            prompt = await self.get_by_name(name)
            if prompt:
                prompt.text = new_text
                await session.commit()

    async def get_by_name(self, name: str) -> Optional[Prompt]:
        async with self.db.async_session() as session:
            result = await session.execute(select(Prompt).where(Prompt.name == name))
            return result.scalar_one_or_none()

    async def get_or_create_by_name(self, name: str, prompt_text: str) -> Prompt:
        async with self.db.async_session() as session:
            existing = await self.get_by_name(name)
            if existing:
                return existing
            new_prompt = Prompt(name=name, text=prompt_text)
            session.add(new_prompt)
            await session.commit()
            return new_prompt
