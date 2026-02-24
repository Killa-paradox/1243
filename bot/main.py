import asyncio
import logging
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

    from bot.config import load_config
    from bot.db import Database
    from bot.handlers import admin, common, errors, seller, start
    from bot.middlewares import AuthMiddleware
    from bot.scheduler import setup_scheduler
else:
    from .config import load_config
    from .db import Database
    from .handlers import admin, common, errors, seller, start
    from .middlewares import AuthMiddleware
    from .scheduler import setup_scheduler

from aiogram import Bot, Dispatcher


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    db = Database(config.db_path)
    await db.init()

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    auth_middleware = AuthMiddleware(db)
    dp.message.middleware(auth_middleware)

    dp.include_router(start.router)
    dp.include_router(common.router)
    dp.include_router(seller.router)
    dp.include_router(admin.router)
    dp.include_router(errors.router)

    scheduler = setup_scheduler(db)
    scheduler.start()

    await dp.start_polling(bot, db=db)


if __name__ == "__main__":
    asyncio.run(main())
