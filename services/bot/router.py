"""Bitta umumiy Router — barcha handlerlar shu yerga ulanadi."""

from aiogram import Router

from services.bot.update_middleware import ChatSerialMiddleware, RateLimitMiddleware

router = Router()

_mw_serial = ChatSerialMiddleware()
_mw_rate = RateLimitMiddleware()

router.message.outer_middleware(_mw_rate)
router.message.outer_middleware(_mw_serial)
router.callback_query.outer_middleware(_mw_rate)
router.callback_query.outer_middleware(_mw_serial)
