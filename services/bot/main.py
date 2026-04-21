"""Botni ishga tushirish.

Aiogram 3: har bir kiruvchi update odatda alohida asyncio taskda ishlaydi
(handle_as_tasks=True — start_polling ning standarti), shuning uchun bir necha
ming foydalanuvchi bir vaqtda yozsa ham handlerlar parallel bajariladi.

FSM: MemoryStorage bitta jarayonda; bir necha serverdan bir token bilan ishlamang
(keyin RedisStorage).
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from packages.db.session import close_engine, init_db
from services.bot.router import router
from shared.config import get_settings

log = logging.getLogger(__name__)


async def run_bot() -> None:
    # Handlerlar routerga ulanishi uchun import (side effect)
    import services.bot.handlers  # noqa: F401

    await init_db()
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    log.info("Bot polling boshlandi")
    try:
        await dp.start_polling(
            bot,
            handle_as_tasks=True,
        )
    finally:
        await bot.session.close()
        await close_engine()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("bot.updates").setLevel(logging.INFO)
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
