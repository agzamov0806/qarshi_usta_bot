"""Bo'lim ustalar ro'yxati."""

from __future__ import annotations

from sqlalchemy import and_, case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import SectionUsta
from shared.phone_norm import format_phone_display, normalize_phone_for_storage


def usta_to_dict(u: SectionUsta) -> dict:
    avg = (u.rating_sum / u.rating_count) if u.rating_count > 0 else None
    return {
        "id": u.id,
        "section_id": int(u.section_id),
        "telegram_id": int(u.telegram_id) if u.telegram_id is not None else None,
        "first_name": u.first_name,
        "last_name": u.last_name or "",
        "display_name": _full_name(u),
        "phone": u.phone,
        "phone_normalized": u.phone_normalized,
        "claimed": u.telegram_id is not None,
        "rating_sum": float(u.rating_sum or 0),
        "rating_count": int(u.rating_count or 0),
        "avg_rating": round(avg, 2) if avg is not None else None,
    }


def _full_name(u: SectionUsta) -> str:
    parts = [u.first_name, u.last_name or ""]
    return " ".join(p for p in parts if p).strip() or u.first_name


async def list_for_section(session: AsyncSession, section_id: int) -> list[dict]:
    q = await session.execute(
        select(SectionUsta)
        .where(SectionUsta.section_id == section_id)
        .order_by(SectionUsta.id.asc())
    )
    return [usta_to_dict(x) for x in q.scalars().all()]


async def list_claimed_for_section(session: AsyncSession, section_id: int) -> list[dict]:
    """Faqat telegram_id bog'langan (buyurtma xabari uchun). Reytingi yuqori usta birinchi."""
    # avg_rating = rating_sum / rating_count; rating_count=0 bo'lsa NULL — oxirga ketadi
    avg_expr = case(
        (SectionUsta.rating_count > 0, SectionUsta.rating_sum / SectionUsta.rating_count),
        else_=None,
    )
    q = await session.execute(
        select(SectionUsta)
        .where(
            SectionUsta.section_id == section_id,
            SectionUsta.telegram_id.is_not(None),
        )
        .order_by(avg_expr.desc().nulls_last(), SectionUsta.id.asc())
    )
    return [usta_to_dict(x) for x in q.scalars().all()]


async def get_by_id(session: AsyncSession, usta_id: int) -> SectionUsta | None:
    return await session.get(SectionUsta, usta_id)


async def add_pending_usta(
    session: AsyncSession,
    *,
    section_id: int,
    first_name: str,
    last_name: str,
    phone: str,
) -> SectionUsta:
    """Telegram ID'siz (pending) usta qo'shish. admin telefon kiritadi."""
    pn = normalize_phone_for_storage(phone)
    u = SectionUsta(
        section_id=section_id,
        telegram_id=None,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=phone.strip(),
        phone_normalized=pn,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


async def delete_usta(session: AsyncSession, usta_id: int) -> bool:
    u = await session.get(SectionUsta, usta_id)
    if not u:
        return False
    await session.delete(u)
    await session.commit()
    return True


async def claim_by_phone(
    session: AsyncSession,
    *,
    contact_phone: str,
    telegram_id: int,
) -> int:
    """
    Usta /start bosgach telefonini yuboradi — mos pending qatorlarga telegram_id yoziladi.
    Bir nechta bo'limda pending bo'lsa, hammasini bog'laydi.
    Qaytadi: yangilangan qatorlar soni.
    """
    pn = normalize_phone_for_storage(contact_phone)
    if not pn:
        return 0
    stmt = (
        update(SectionUsta)
        .where(
            and_(
                SectionUsta.phone_normalized == pn,
                SectionUsta.telegram_id.is_(None),
            )
        )
        .values(telegram_id=telegram_id)
    )
    res = await session.execute(stmt)
    await session.commit()
    return int(res.rowcount)


async def find_pending_by_normalized_phone(
    session: AsyncSession, phone_normalized: str
) -> list[SectionUsta]:
    """Kutilayotgan qatorlarni telefon bo'yicha topish (tekshirish uchun)."""
    q = await session.execute(
        select(SectionUsta).where(
            and_(
                SectionUsta.phone_normalized == phone_normalized,
                SectionUsta.telegram_id.is_(None),
            )
        )
    )
    return list(q.scalars().all())


async def is_registered_as_usta(
    session: AsyncSession, telegram_id: int
) -> bool:
    q = await session.execute(
        select(SectionUsta.id).where(
            SectionUsta.telegram_id == telegram_id
        ).limit(1)
    )
    return q.scalar_one_or_none() is not None


async def add_rating(session: AsyncSession, *, usta_id: int, rating: int) -> bool:
    """Ustaga baho qo'shish (1-5). rating_sum va rating_count yangilanadi."""
    stmt = (
        update(SectionUsta)
        .where(SectionUsta.id == usta_id)
        .values(
            rating_sum=SectionUsta.rating_sum + rating,
            rating_count=SectionUsta.rating_count + 1,
        )
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount > 0
