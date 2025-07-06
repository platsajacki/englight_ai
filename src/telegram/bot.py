from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage

from telegram.middlewares.retry_after import LimiterMiddleware

TOKEN = getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError('BOT_TOKEN environment variable is not set.')

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
router.message.middleware(LimiterMiddleware())

dp.include_router(router)
