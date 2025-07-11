from aiogram.types import BufferedInputFile

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from constants import ADMIN_ID, SCHEDULED_TIMES, UTC
from database.database import db
from database.managers import WordProgressManager
from telegram.bot import bot
from telegram.buttons import make_know_or_not_buttons
from utils import text_to_speech


def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone=UTC)
    for t in SCHEDULED_TIMES:
        scheduler.add_job(send_word_reviews, 'cron', hour=t.hour, minute=t.minute)
    scheduler.start()


async def send_word_reviews():
    async with db.async_session() as session:
        word_progress_manager = WordProgressManager(session)
        word_progresses = await word_progress_manager.get_next_review_words()
        if not word_progresses:
            await bot.send_message(chat_id=ADMIN_ID, text='No words to review at this time.')
            return
        for word_progress in word_progresses:
            if not word_progress.word.word:
                continue
            audio = await text_to_speech(word_progress.word.word)
            await bot.send_voice(
                chat_id=ADMIN_ID,
                voice=BufferedInputFile(audio, filename=f'{word_progress.word.word}.mp3'),
            )
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=word_progress.word.word,
                reply_markup=make_know_or_not_buttons(word_progress.word.id),
            )
