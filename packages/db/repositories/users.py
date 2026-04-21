"""Foydalanuvchilar (ro'yxatdan o'tish)."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import User

LANG_UZ = "uz"
LANG_RU = "ru"

# get_locale — har handlerda DB so'rovsiz (TTL)
_locale_memo: dict[int, tuple[str, float]] = {}
_LOCALE_TTL_SEC = 45.0


def _bump_locale_memo(telegram_id: int, loc: str) -> None:
    _locale_memo[telegram_id] = (loc, time.monotonic())


def invalidate_locale_cache(telegram_id: int) -> None:
    _locale_memo.pop(telegram_id, None)


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.get(User, telegram_id)


async def is_registered(session: AsyncSession, telegram_id: int) -> bool:
    u = await get_user(session, telegram_id)
    return u is not None


async def save_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    first_name: str,
    last_name: str,
    phone: str,
    locale: str | None = None,
) -> None:
    existing = await get_user(session, telegram_id)
    now = datetime.now(timezone.utc)
    loc_new = LANG_UZ
    if locale is not None:
        loc = locale.strip().lower()
        if loc in (LANG_UZ, LANG_RU):
            loc_new = loc
    if existing:
        existing.first_name = first_name.strip()
        existing.last_name = last_name.strip()
        existing.phone = phone.strip()
        existing.registered_at = now
        if locale is not None:
            existing.locale = loc_new
    else:
        session.add(
            User(
                telegram_id=telegram_id,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                phone=phone.strip(),
                locale=loc_new,
                registered_at=now,
            )
        )
    await session.commit()
    invalidate_locale_cache(telegram_id)


async def get_locale(session: AsyncSession, telegram_id: int) -> str:
    now = time.monotonic()
    hit = _locale_memo.get(telegram_id)
    if hit is not None:
        loc_mem, ts = hit
        if now - ts < _LOCALE_TTL_SEC:
            return loc_mem
    u = await get_user(session, telegram_id)
    if not u:
        loc = LANG_UZ
    else:
        loc = (u.locale or LANG_UZ).strip().lower()
        loc = loc if loc in (LANG_UZ, LANG_RU) else LANG_UZ
    _bump_locale_memo(telegram_id, loc)
    return loc


async def set_locale(session: AsyncSession, telegram_id: int, locale: str) -> None:
    loc = locale.strip().lower() if locale else LANG_UZ
    if loc not in (LANG_UZ, LANG_RU):
        loc = LANG_UZ
    u = await get_user(session, telegram_id)
    if not u:
        return
    u.locale = loc
    await session.commit()
    _bump_locale_memo(telegram_id, loc)
