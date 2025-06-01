import asyncio
import logging
import sys
from logging import basicConfig

from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from dotenv import load_dotenv

from constants import JSON_FORMAT, PromptName
from core.gemini import GeminiEnglight
from database.database import db
from database.managers import PromptManager
from telegram.bot import bot, dp, router
from telegram.states import PromptStates


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if not message.from_user:
        return
    await message.answer(f'Hello, {message.from_user.full_name}!')


@router.message(Command('update_translate_prompt'))
async def update_translate_prompt_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    await message.answer('Input new translate prompt text:')
    await state.set_state(PromptStates.waiting_for_translate_prompt)


@router.message(PromptStates.waiting_for_translate_prompt)
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


@router.message(StateFilter(None))
async def handle_all_messages(message: Message) -> None:
    text = message.text
    if not text:
        return
    answers = await GeminiEnglight(text)()
    for answer in answers:
        await message.answer(str(answer), parse_mode=ParseMode.HTML)


async def main() -> None:
    await db.init_models()
    await dp.start_polling(bot)


if __name__ == '__main__':
    load_dotenv()
    basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
