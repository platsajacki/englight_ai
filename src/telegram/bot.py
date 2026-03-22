from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from telegram.middlewares.retry_after import LimiterMiddleware
from constants import PROXY_URL

TOKEN = getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError('BOT_TOKEN environment variable is not set.')

session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else AiohttpSession()
bot = Bot(token=TOKEN, session=session)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
router.message.middleware(LimiterMiddleware())

dp.include_router(router)
