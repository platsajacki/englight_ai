from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import BufferedInputFile

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from constants import ALLOWED_CHATS, SCHEDULED_TIMES, UTC, WORD_PER_TIME
from core.loggers import app_logger as logger
from database.database import db
from database.managers import UserManager, WordProgressManager
from database.models import User, Word
from telegram.bot import bot
from telegram.buttons import make_know_or_not_buttons
from utils import text_to_speech


class ReviewSender:
    async def send_all(self) -> None:
        for user in await self.get_allowed_users():
            try:
                await self.send_to_user(user)
            except (TelegramForbiddenError, TelegramBadRequest) as e:
                logger.warning('Could not send word reviews to user %s: %s', user.telegram_id, e)
            except Exception as e:
                logger.error('Failed to send word reviews to user %s: %s', user.telegram_id, e, exc_info=True)

    @staticmethod
    async def get_allowed_users() -> list[User]:
        telegram_ids = [int(chat) for chat in ALLOWED_CHATS if chat.lstrip('-').isdigit()]
        async with db.async_session() as session:
            return list(await UserManager(session).get_by_telegram_ids(telegram_ids))

    async def send_to_user(self, user: User) -> None:
        async with db.async_session() as session:
            word_progresses = await WordProgressManager(session).get_next_review_words(user.id, WORD_PER_TIME)
        for word_progress in word_progresses:
            if word_progress.word.word:
                await self.send_word(user.telegram_id, word_progress.word)

    @staticmethod
    async def send_word(chat_id: int, word: Word) -> None:
        audio = await text_to_speech(word.word or '')
        await bot.send_voice(chat_id=chat_id, voice=BufferedInputFile(audio, filename=f'{word.word}.mp3'))
        await bot.send_message(chat_id=chat_id, text=word.word or '', reply_markup=make_know_or_not_buttons(word.id))


def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone=UTC)
    for t in SCHEDULED_TIMES:
        scheduler.add_job(ReviewSender().send_all, 'cron', hour=t.hour, minute=t.minute)
    scheduler.start()
