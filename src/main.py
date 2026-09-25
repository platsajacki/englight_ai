import asyncio
from typing import Sequence

from aiogram import F
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from dotenv import load_dotenv

from constants import PROMPT_PLACEHOLDERS, PromptName
from core.loggers import app_logger as logger
from core.loggers import setup_logging
from core.openai import OpenAIAnswer, OpenAIEnglight, describe_openai_error
from core.scheduler import setup_scheduler
from core.sentence_check import SentenceError, SentenceReview, SentenceSource
from database.database import db
from database.managers import PromptManager, WordManager, WordProgressManager
from database.models import User, Word, WordProgress
from telegram.bot import bot, dp, router
from telegram.buttons import make_cancel_check_button, make_delete_buttons, make_got_it_button
from telegram.filters import access_filter, admin_filter, private_user_filter
from telegram.reports import StatsReport
from telegram.states import PromptStates, ReviewStates
from utils import text_to_speech

PROMPT_COMMANDS = {
    'update_translate_prompt': PromptName.TRANSLATE,
    'update_check_prompt': PromptName.CHECK_SENTENCE,
}


@router.message(CommandStart(), access_filter)
async def command_start_handler(message: Message) -> None:
    if not message.from_user:
        return
    await message.answer(f'Hello, {message.from_user.full_name}!')


@router.message(Command(*PROMPT_COMMANDS), access_filter, admin_filter)
async def update_prompt_handler(message: Message, command: CommandObject, state: FSMContext) -> None:
    prompt_name = PROMPT_COMMANDS[command.command]
    await state.set_state(PromptStates.waiting_for_prompt)
    await state.update_data(prompt_name=prompt_name)
    placeholders = ', '.join(PROMPT_PLACEHOLDERS[prompt_name])
    await message.answer(f'Input new {prompt_name} prompt text. Required placeholders: {placeholders}')


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


@router.message(PromptStates.waiting_for_prompt, access_filter, admin_filter)
async def waiting_for_prompt_handler(message: Message, state: FSMContext) -> None:
    prompt_name = (await state.get_data())['prompt_name']
    new_text = message.text or ''
    missing = [placeholder for placeholder in PROMPT_PLACEHOLDERS[prompt_name] if placeholder not in new_text]
    if missing:
        await message.answer(f'Prompt text must contain placeholders: {", ".join(missing)}')
        return
    async with db.async_session() as session:
        await PromptManager(session).update_text_by_name(prompt_name, new_text)
    await message.answer(f'Prompt "{prompt_name}" updated successfully.')
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
async def handle_know_not_know(callback_query: CallbackQuery, state: FSMContext) -> None:
    if callback_query.data is None or callback_query.message is None:
        return
    data = callback_query.data.split('_')
    async with db.async_session() as session:
        word = await WordManager(session).get_with_examples(int(data[-1]))
    if not word:
        await edit_callback_message(callback_query, 'Word not found.')
        return
    if data[0] == 'know':
        await start_sentence_check(callback_query, state, word)
        return
    await edit_callback_message(callback_query, word.to_message(), make_got_it_button(word.id))


async def start_sentence_check(callback_query: CallbackQuery, state: FSMContext, word: Word) -> None:
    await state.set_state(ReviewStates.waiting_for_sentence)
    await state.update_data(word_id=word.id)
    text = f'Say or write a sentence with <b>{word.word}</b> ({word.part_of_speech}).'
    await edit_callback_message(callback_query, text, make_cancel_check_button(word.id))


@router.message(ReviewStates.waiting_for_sentence, ~F.text.startswith('/'), access_filter, private_user_filter)
async def handle_sentence(message: Message, state: FSMContext, user: User) -> None:
    word_id = (await state.get_data())['word_id']
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        answer = await SentenceReview(user, word_id).check(await SentenceSource.extract(message))
    except SentenceError as e:
        await message.answer(str(e))
        return
    except Exception as e:
        await message.answer(describe_openai_error(e))
        return
    await state.clear()
    await send_openai_answer(message, answer)


@router.callback_query(F.data.startswith('cancel_check_'), access_filter)
async def handle_cancel_check(callback_query: CallbackQuery, state: FSMContext) -> None:
    if callback_query.data is None:
        return
    word_id = int(callback_query.data.removeprefix('cancel_check_'))
    if (await state.get_data()).get('word_id') == word_id:
        await state.clear()
    await edit_callback_message(callback_query, 'Check cancelled. Word progress is unchanged.')


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


async def edit_callback_message(
    callback_query: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    message = callback_query.message
    await message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)  # type: ignore[union-attr]


async def main() -> None:
    await db.init_models()
    setup_scheduler()
    await dp.start_polling(bot)


if __name__ == '__main__':
    load_dotenv()
    setup_logging()
    asyncio.run(main())
