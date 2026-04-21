"""Bitta umumiy Router — barcha handlerlar shu yerga ulanadi."""

from aiogram import Router

from services.bot.update_middleware import ChatSerialMiddleware

router = Router()

_mw = ChatSerialMiddleware()
router.message.outer_middleware(_mw)
router.callback_query.outer_middleware(_mw)
