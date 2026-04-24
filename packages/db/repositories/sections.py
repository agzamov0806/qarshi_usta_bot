"""Xizmat bo'limlari (CRUD)."""

from __future__ import annotations

import time

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Any

from packages.db.models import Section, SectionUsta

_UNSET: Any = object()
from shared.section_titles import canonical_title_for_lookup

# Tur nomlari (DB da saqlanadi)
KIND_STANDARD = "standard"
KIND_SUGGESTION = "suggestion"
KIND_ADMIN_CONTACT = "admin_contact"

KIND_LABELS = {
    KIND_STANDARD: "Oddiy buyurtma",
    KIND_SUGGESTION: "Taklif",
    KIND_ADMIN_CONTACT: "Adminga murojaat",
}

# list_active_titles uchun — har xabar uchun qayta-qayta SELECTsiz
_titles_cache: list[str] | None = None
_titles_cache_ts: float = 0.0
_TITLES_CACHE_TTL_SEC = 45.0


def invalidate_active_titles_cache() -> None:
    """Bo'lim CRUD dan keyin chaqirish."""
    global _titles_cache
    _titles_cache = None


def _titles_cache_valid(now: float) -> bool:
    return (
        _titles_cache is not None
        and (now - _titles_cache_ts) < _TITLES_CACHE_TTL_SEC
    )


def section_to_dict(s: Section) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "sort_order": s.sort_order,
        "is_active": s.is_active,
        "kind": s.kind,
        "usta_telegram_id": s.usta_telegram_id,
        "created_at": s.created_at,
    }


async def list_all(session: AsyncSession) -> list[dict]:
    q = await session.execute(
        select(Section).order_by(Section.sort_order.asc(), Section.id.asc())
    )
    secs = list(q.scalars().all())
    if not secs:
        return []
    ids = [int(s.id) for s in secs]
    cq = await session.execute(
        select(SectionUsta.section_id, func.count(SectionUsta.id))
        .where(SectionUsta.section_id.in_(ids))
        .group_by(SectionUsta.section_id)
    )
    usta_counts = {int(r[0]): int(r[1]) for r in cq.all()}
    out: list[dict] = []
    for x in secs:
        d = section_to_dict(x)
        d["usta_count"] = usta_counts.get(int(x.id), 0)
        out.append(d)
    return out


async def _fetch_active_titles_from_db(session: AsyncSession) -> list[str]:
    q = await session.execute(
        select(Section.title)
        .where(Section.is_active.is_(True))
        .order_by(Section.sort_order.asc(), Section.id.asc())
    )
    return [r[0] for r in q.all()]


async def list_active_titles(session: AsyncSession) -> list[str]:
    global _titles_cache, _titles_cache_ts
    now = time.monotonic()
    if _titles_cache_valid(now):
        return list(_titles_cache or [])
    rows = await _fetch_active_titles_from_db(session)
    _titles_cache = rows
    _titles_cache_ts = now
    return list(rows)


async def get_by_id(session: AsyncSession, section_id: int) -> Section | None:
    return await session.get(Section, section_id)


async def get_active_by_title(session: AsyncSession, title: str) -> Section | None:
    t = canonical_title_for_lookup(title)
    titles = await list_active_titles(session)
    if t not in titles:
        return None
    q = await session.execute(
        select(Section).where(
            Section.title == t,
            Section.is_active.is_(True),
        )
    )
    return q.scalar_one_or_none()


async def create_section(
    session: AsyncSession,
    *,
    title: str,
    kind: str = KIND_STANDARD,
    sort_order: int | None = None,
) -> Section:
    if sort_order is None:
        r = await session.execute(select(func.coalesce(func.max(Section.sort_order), -1)))
        sort_order = int(r.scalar_one()) + 1
    s = Section(
        title=title.strip(),
        kind=kind,
        sort_order=sort_order,
        is_active=True,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    invalidate_active_titles_cache()
    return s


async def update_section(
    session: AsyncSession,
    section_id: int,
    *,
    title: str | None = None,
    kind: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
    usta_telegram_id: int | None | Any = _UNSET,
) -> bool:
    s = await session.get(Section, section_id)
    if not s:
        return False
    if title is not None:
        s.title = title.strip()
    if kind is not None:
        s.kind = kind
    if sort_order is not None:
        s.sort_order = sort_order
    if is_active is not None:
        s.is_active = is_active
    if usta_telegram_id is not _UNSET:
        s.usta_telegram_id = usta_telegram_id
    await session.commit()
    invalidate_active_titles_cache()
    return True


async def delete_section(session: AsyncSession, section_id: int) -> bool:
    s = await session.get(Section, section_id)
    if not s:
        return False
    await session.delete(s)
    await session.commit()
    invalidate_active_titles_cache()
    return True


async def count_sections(session: AsyncSession) -> int:
    r = await session.execute(select(func.count()).select_from(Section))
    return int(r.scalar_one())


async def seed_defaults_if_empty(session: AsyncSession) -> None:
    if await count_sections(session) > 0:
        return
    defaults: list[tuple[str, str, int]] = [
        ("Santexnika", KIND_STANDARD, 0),
        ("Elektrik", KIND_STANDARD, 1),
        ("Konditsioner", KIND_STANDARD, 2),
        ("Payvandlash xizmati (svarka)", KIND_STANDARD, 3),
        ("Mebel yig'ish xizmati", KIND_STANDARD, 4),
        ("Televizor va boshqa maishiy texnika ta'miri", KIND_STANDARD, 5),
        ("Takliflar", KIND_SUGGESTION, 6),
        ("Adminga murojaat", KIND_ADMIN_CONTACT, 7),
    ]
    for title, kind, order in defaults:
        session.add(
            Section(
                title=title,
                kind=kind,
                sort_order=order,
                is_active=True,
            )
        )
    await session.commit()
    invalidate_active_titles_cache()
