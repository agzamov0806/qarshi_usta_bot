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

    # Startup: Pending ustalarga admin xabar
    await _notify_pending_ustas_on_startup(bot, settings)

    log.info("Bot polling boshlandi")
    try:
        await dp.start_polling(
            bot,
            handle_as_tasks=True,
        )
    finally:
        await bot.session.close()
        await close_engine()


async def _notify_pending_ustas_on_startup(bot: Bot, settings) -> None:
    """Bot startup paytida pending ustalarga admin xabar."""
    try:
        from packages.db.session import get_session
        from packages.db.repositories import section_ustas as su_repo

        async for session in get_session():
            pending = await su_repo.list_pending_approval(session)
            if not pending:
                return

            # Pending ustalari ro'yxati
            lines = ["⏳ <b>BOT QAYTA ISHGA TUSHDI</b>\n"]
            lines.append(f"Pending ariza: {len(pending)}\n")
            for i, u in enumerate(pending, 1):
                name = u.get("display_name", "?")
                lines.append(f"{i}. {name}")

            text = "\n".join(lines)
            await bot.send_message(
                chat_id=settings.admin_chat_id,
                text=text,
                parse_mode="HTML",
            )
            log.info("startup_notification: pending_count=%d", len(pending))
            break
    except Exception as exc:
        log.error("startup_notification_failed: %s", exc)


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
