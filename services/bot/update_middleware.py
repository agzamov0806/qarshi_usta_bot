"""Bitta chat bo‘yicha update-larni ketma-ket ishlatish va loglar.

Sabab: handle_as_tasks=True paytida bir foydalanuvchidan tez ket-ket bosilgan
tugmalar turli asyncio vazifalarida bir vaqtda ishlaydi. Handler ichida
await (masalan DB) bo‘lguncha keyingi update allaqachon FSM ning eski holatida
ishga tushishi va bir xabar bir necha marta qayta ishlashi mumkin."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

log = logging.getLogger("bot.updates")


def _serial_key(event: TelegramObject) -> int | None:
    if isinstance(event, Message):
        return event.chat.id
    if isinstance(event, CallbackQuery):
        if event.message is not None:
            return event.message.chat.id
        if event.from_user is not None:
            return int(event.from_user.id)
    return None


class ChatSerialMiddleware(BaseMiddleware):
    """Chat / foydalanuvchi bo‘yicha bir vaqtda faqat bitta handler ishlaydi."""

    __slots__ = ("_locks",)

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock(self, key: int) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        ev: Update | None = data.get("event_update")
        update_id = ev.update_id if ev else None
        key = _serial_key(event)

        if key is None:
            log.debug(
                "dispatch update_id=%s type=%s (serial skipped)",
                update_id,
                type(event).__name__,
            )
            return await handler(event, data)

        lock = self._lock(key)
        async with lock:
            text_preview: str | None = None
            mid: int | None = None
            if isinstance(event, Message):
                mid = event.message_id
                if event.text:
                    t = event.text
                    text_preview = t if len(t) <= 100 else t[:97] + "..."
            elif isinstance(event, CallbackQuery):
                mid = event.message.message_id if event.message else None
                if event.data:
                    d = event.data
                    text_preview = d if len(d) <= 100 else d[:97] + "..."

            log.info(
                "dispatch update_id=%s chat_or_user=%s event=%s mid=%s text=%r",
                update_id,
                key,
                type(event).__name__,
                mid,
                text_preview,
            )
            result = await handler(event, data)
            log.debug("handled update_id=%s chat_or_user=%s", update_id, key)
            return result
