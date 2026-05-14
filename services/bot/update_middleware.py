"""Bitta chat bo’yicha update-larni ketma-ket ishlatish va loglar.

Sabab: handle_as_tasks=True paytida bir foydalanuvchidan tez ket-ket bosilgan
tugmalar turli asyncio vazifalarida bir vaqtda ishlaydi. Handler ichida
await (masalan DB) bo’lguncha keyingi update allaqachon FSM ning eski holatida
ishga tushishi va bir xabar bir necha marta qayta ishlashi mumkin."""
from __future__ import annotations

import asyncio
import logging
import time
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
        return self._locks.setdefault(key, asyncio.Lock())

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


class RateLimitMiddleware(BaseMiddleware):
    """Har bir foydalanuvchiga rate limit qo'yish — spam oldini olish."""

    __slots__ = ("_user_timestamps",)
    # max_messages per second per user
    MAX_MESSAGES_PER_SEC = 5

    def __init__(self) -> None:
        self._user_timestamps: dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        key = _serial_key(event)
        if key is None:
            return await handler(event, data)

        now = time.time()
        if key not in self._user_timestamps:
            self._user_timestamps[key] = []

        # Keep only timestamps from last second
        self._user_timestamps[key] = [
            ts for ts in self._user_timestamps[key] if now - ts < 1.0
        ]

        # Check rate limit
        if len(self._user_timestamps[key]) >= self.MAX_MESSAGES_PER_SEC:
            log.warning(
                "rate_limit exceeded for user=%s messages_in_1s=%d",
                key,
                len(self._user_timestamps[key]),
            )
            # Skip this update silently to prevent spam loops
            return None

        # Record this message
        self._user_timestamps[key].append(now)

        return await handler(event, data)
