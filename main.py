from aiogram import Dispatcher, Bot
from app.executer_handlers import router, reminders
import asyncio

from config import TOKEN

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:

        print('bot started')
        asyncio.run(main())
    except KeyboardInterrupt:
        print('bot deactivated')