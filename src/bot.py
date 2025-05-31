from os import getenv

from aiogram import Bot, Dispatcher, Router

TOKEN = getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError('BOT_TOKEN environment variable is not set.')

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

dp.include_router(router)
