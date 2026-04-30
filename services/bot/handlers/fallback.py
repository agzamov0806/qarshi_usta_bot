"""Oxirgi handler: boshqa hech qaysi filter mos kelmaganda."""

import logging

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from packages.db.repositories import users as users_repo
from packages.db.session import get_session_factory
from services.bot.i18n import (
    nested_entry_list_labels,
    nested_entry_manual_labels,
    t,
)
from services.bot.router import router

log = logging.getLogger(__name__)

_ORPHAN_NESTED_BTN_TEXTS = frozenset(
    nested_entry_list_labels() + nested_entry_manual_labels()
)


@router.message(
    F.text,
    F.chat.type == ChatType.PRIVATE,
    StateFilter(None),
    F.text.in_(_ORPHAN_NESTED_BTN_TEXTS),
)
async def fallback_orphan_nested_keyboard(message: Message) -> None:
    """Holat yo'q lekin avvalgi «Ro'yxat / qo'lda» tugmalari qolgan (MemoryStorage restart yoki boshqa server)."""
    uid = message.from_user.id if message.from_user else 0
    async with get_session_factory()() as session:
        loc = await users_repo.get_locale(session, uid)
    await message.answer(
        t(loc, "fallback.orphaned_nested"),
        parse_mode="HTML",
    )


@router.message(F.text, F.chat.type == ChatType.PRIVATE)
async def fallback_unhandled_private_text(message: Message, state: FSMContext) -> None:
    """Shu modul routerda oxirgi import qilinadi — faqat 'tushib qolgan' matnlar."""
    st = await state.get_state()
    uid = message.from_user.id if message.from_user else 0
    log.warning(
        "handler mos kelmadi: chat=%s uid=%s state=%s text=%r",
        message.chat.id,
        uid,
        st,
        (message.text or "")[:200],
    )
    async with get_session_factory()() as session:
        loc = await users_repo.get_locale(session, uid)
    await message.answer(t(loc, "fallback.no_handler"))
