import asyncio
import logging
import sys
from logging import basicConfig

from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from dotenv import load_dotenv

from constants import ALLOWED_CHATS_FOR_SAVING_TO_DB, JSON_FORMAT, PromptName
from core.gemini import GeminiEnglight
from core.scheduler import setup_scheduler
from database.database import db
from database.managers import PromptManager, WordManager, WordProgressManager
from telegram.bot import bot, dp, router
from telegram.buttons import make_sure_buttons
from telegram.filters import access_filter
from telegram.states import PromptStates


@router.message(CommandStart(), access_filter)
async def command_start_handler(message: Message) -> None:
    if not message.from_user:
        return
    await message.answer(f'Hello, {message.from_user.full_name}!')


@router.message(Command('update_translate_prompt'), access_filter)
async def update_translate_prompt_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    await message.answer('Input new translate prompt text:')
    await state.set_state(PromptStates.waiting_for_translate_prompt)


@router.message(Command('count_words'), access_filter)
async def count_words_handler(message: Message) -> None:
    if not message.from_user:
        return
    words = await WordManager(db).all()
    response = f'Total words in the database: {len(words)}'
    await message.answer(response)


@router.message(PromptStates.waiting_for_translate_prompt, access_filter)
async def waiting_for_translate_prompt_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    new_text = message.text
    if not new_text:
        await message.answer('Prompt text cannot be empty.')
        return
    if '{message}' not in new_text:
        await message.answer('Prompt text must contain "{message}" placeholder.')
        return
    if JSON_FORMAT not in new_text:
        await message.answer(f'Prompt text must contain:\n{JSON_FORMAT}')
        return
    prompt_manager = PromptManager(db)
    await prompt_manager.update_text_by_name(PromptName.TRANSLATE, new_text)
    await message.answer('Translate prompt updated successfully.')
    await state.clear()


@router.message(StateFilter(None), access_filter)
async def handle_all_messages(message: Message) -> None:
    text = message.text
    if not text:
        return
    save_to_db = str(message.chat.id) in ALLOWED_CHATS_FOR_SAVING_TO_DB
    answers = await GeminiEnglight(text, save_to_db)()
    for answer in answers:
        await message.answer(str(answer), parse_mode=ParseMode.HTML)


@router.callback_query(lambda c: c.data.startswith('know_') or c.data.startswith('not_know_'), access_filter)
async def handle_know_not_know(callback_query: CallbackQuery):
    if callback_query.data is None or callback_query.message is None:
        return
    word_id = int(callback_query.data.split('_')[1])
    word_manager = WordManager(db)
    word = await word_manager.get_with_examples(word_id)
    if not word:
        await callback_query.message.answer('Word not found.')
        return
    await callback_query.message.answer(
        word.to_message(),
        parse_mode=ParseMode.HTML,
        reply_markup=make_sure_buttons(word_id),
    )


@router.callback_query(lambda c: c.data.startswith('sure_'), access_filter)
async def handle_sure(callback_query: CallbackQuery) -> None:
    if callback_query.message is None or callback_query.data is None:
        return
    _, answer, word_id_str = callback_query.data.split('_')
    word_id = int(word_id_str)
    word_progress_manager = WordProgressManager(db)
    word_progress = word_progress_manager.record_review(word_id, answer == 'yes')
    if not word_progress:
        await callback_query.message.answer('Word progress not found.')
        return
    await callback_query.message.answer('I updated the word progress. Thanks for your answer!')


async def main() -> None:
    await db.init_models()
    setup_scheduler()
    await dp.start_polling(bot)


if __name__ == '__main__':
    load_dotenv()
    basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
