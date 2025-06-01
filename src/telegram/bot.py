from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError('BOT_TOKEN environment variable is not set.')

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

dp.include_router(router)
