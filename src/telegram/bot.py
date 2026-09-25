from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from constants import PROXY_URL
from telegram.middlewares.retry_after import LimiterMiddleware
from telegram.middlewares.user import UserMiddleware

TOKEN = getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError('BOT_TOKEN environment variable is not set.')

session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else AiohttpSession()
bot = Bot(token=TOKEN, session=session)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
router.message.middleware(LimiterMiddleware())
router.message.outer_middleware(UserMiddleware())
router.callback_query.outer_middleware(UserMiddleware())

dp.include_router(router)
