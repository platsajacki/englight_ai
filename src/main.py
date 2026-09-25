import asyncio
from typing import Sequence

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from dotenv import load_dotenv

from constants import PromptName
from core.loggers import app_logger as logger
from core.loggers import setup_logging
from core.openai import OpenAIAnswer, OpenAIEnglight
from core.scheduler import setup_scheduler
from database.database import db
from database.managers import PromptManager, WordManager, WordProgressManager
from database.models import User, WordProgress
from telegram.bot import bot, dp, router
from telegram.buttons import make_delete_buttons, make_sure_buttons
from telegram.filters import access_filter, admin_filter, private_user_filter
from telegram.reports import StatsReport
from telegram.states import PromptStates
from utils import text_to_speech


@router.message(CommandStart(), access_filter)
async def command_start_handler(message: Message) -> None:
    if not message.from_user:
        return
    await message.answer(f'Hello, {message.from_user.full_name}!')


@router.message(Command('update_translate_prompt'), access_filter, admin_filter)
async def update_translate_prompt_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    await message.answer('Input new translate prompt text:')
    await state.set_state(PromptStates.waiting_for_translate_prompt)


@router.message(Command('count_words'), access_filter, private_user_filter)
async def count_words_handler(message: Message, user: User) -> None:
    async with db.async_session() as session:
        progresses = await WordProgressManager(session).all_for_user(user.id)
    await message.answer(f'Total words in your list: {len(progresses)}')


@router.message(Command('stats'), access_filter, private_user_filter)
async def stats_handler(message: Message, user: User) -> None:
    async with db.async_session() as session:
        progresses = await WordProgressManager(session).all_for_user(user.id)
    await message.answer(StatsReport(progresses).render(), parse_mode=ParseMode.HTML)


@router.message(Command('delete_word'), access_filter, private_user_filter)
async def delete_word_handler(message: Message, command: CommandObject, user: User) -> None:
    if not command.args:
        await message.answer('Usage: /delete_word <word>')
        return
    async with db.async_session() as session:
        progresses = await WordProgressManager(session).find_for_user_by_word(user.id, command.args.strip())
    await answer_delete_candidates(message, user, progresses)


async def answer_delete_candidates(message: Message, user: User, progresses: Sequence[WordProgress]) -> None:
    if len(progresses) > 1:
        buttons = make_delete_buttons([(wp.word_id, wp.word.part_of_speech or '?') for wp in progresses])
        await message.answer('Which one do you want to delete?', reply_markup=buttons)
        return
    text = await delete_user_word(user, progresses[0].word_id) if progresses else 'Word not found in your list.'
    await message.answer(text, parse_mode=ParseMode.HTML)


async def delete_user_word(user: User, word_id: int) -> str:
    async with db.async_session() as session:
        word_progress = await WordProgressManager(session).delete_for_user(user.id, word_id)
    if not word_progress:
        return 'Word not found in your list.'
    word = word_progress.word
    return f'Word <b>{word.word}</b> ({word.part_of_speech}) deleted from your list.'


@router.message(PromptStates.waiting_for_translate_prompt, access_filter, admin_filter)
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
    async with db.async_session() as session:
        prompt_manager = PromptManager(session)
        await prompt_manager.update_text_by_name(PromptName.TRANSLATE, new_text)
        await message.answer('Translate prompt updated successfully.')
        await state.clear()


@router.message(StateFilter(None), ~F.text.startswith('/'), access_filter)
async def handle_all_messages(message: Message, user: User | None) -> None:
    text = message.text
    if not text:
        return
    answers = await OpenAIEnglight(text, user.id if user else None)()
    for answer in answers:
        await send_openai_answer(message, answer)


async def send_openai_answer(message: Message, answer: OpenAIAnswer) -> None:
    await message.answer(answer.text, parse_mode=ParseMode.HTML)
    if not answer.audio_text:
        return
    try:
        audio = await text_to_speech(answer.audio_text)
        voice = BufferedInputFile(audio, filename='pronunciation.mp3')
        await message.answer_voice(voice)
    except Exception as e:
        logger.error('Could not generate pronunciation for "%s": %s', answer.audio_text, e, exc_info=True)
        await message.answer('Could not generate pronunciation audio. Try again later.')


@router.callback_query(lambda c: c.data.startswith('know_') or c.data.startswith('not_know_'), access_filter)
async def handle_know_not_know(callback_query: CallbackQuery):
    if callback_query.data is None or callback_query.message is None:
        return
    data = callback_query.data.split('_')
    word_id = int(data[-1])
    async with db.async_session() as session:
        word_manager = WordManager(session)
        word = await word_manager.get_with_examples(word_id)
        if not word:
            await callback_query.message.edit_text('Word not found.')  # type: ignore[union-attr]
            return
        is_know = data[0] == 'know'
        msg = f'{word.to_message()}\n\n <i>Do you really know this word?</i>' if is_know else word.to_message()
        await callback_query.message.edit_text(  # type: ignore[union-attr]
            msg,
            parse_mode=ParseMode.HTML,
            reply_markup=make_sure_buttons(word_id, is_know=is_know),
        )


@router.callback_query(lambda c: c.data.startswith('sure_'), access_filter, private_user_filter)
async def handle_sure(callback_query: CallbackQuery, user: User) -> None:
    if callback_query.message is None or callback_query.data is None:
        return
    _, answer, word_id_str = callback_query.data.split('_')
    async with db.async_session() as session:
        word_progress = await WordProgressManager(session).record_review(user.id, int(word_id_str), answer == 'yes')
    text = (
        f'I updated word "<b>{word_progress.word.word or 'WAS EMPTY'}"</b> progress. Thanks for your answer!'
        if word_progress
        else 'Word progress not found.'
    )
    await edit_callback_message(callback_query, text)


@router.callback_query(F.data.startswith('delete_'), access_filter, private_user_filter)
async def handle_delete(callback_query: CallbackQuery, user: User) -> None:
    if callback_query.message is None or callback_query.data is None:
        return
    text = await delete_user_word(user, int(callback_query.data.removeprefix('delete_')))
    await edit_callback_message(callback_query, text)


async def edit_callback_message(callback_query: CallbackQuery, text: str) -> None:
    message = callback_query.message
    await message.edit_text(text, reply_markup=None, parse_mode=ParseMode.HTML)  # type: ignore[union-attr]


async def main() -> None:
    await db.init_models()
    setup_scheduler()
    await dp.start_polling(bot)


if __name__ == '__main__':
    load_dotenv()
    setup_logging()
    asyncio.run(main())
