import asyncio
import logging
import sys
from logging import basicConfig

from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from dotenv import load_dotenv

from bot import bot, dp, router
from gemini import GeminiEnglight


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if not message.from_user:
        return
    await message.answer(f'Hello, {message.from_user.full_name}!')


@router.message()
async def handle_all_messages(message: Message) -> None:
    text = message.text
    if not text:
        return
    answers = GeminiEnglight(text)()
    for answer in answers:
        await message.answer(str(answer), parse_mode=ParseMode.HTML)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == '__main__':
    load_dotenv()
    basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
