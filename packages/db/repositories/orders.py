"""Buyurtmalar."""

from typing import Literal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import Order, SectionUsta
from shared.tz import format_dt_uz, utc_day_bounds_for_today_uz


def order_to_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "created_at": format_dt_uz(o.created_at) if o.created_at else "",
        "client_tg_id": o.client_tg_id,
        "client_name": o.client_name,
        "username": o.username,
        "phone": o.phone,
        "service": o.service,
        "section_id": o.section_id,
        "section_kind": o.section_kind,
        "problem": o.problem,
        "problem_media_json": o.problem_media_json,
        "lat": o.lat,
        "lon": o.lon,
        "service_address_note": o.service_address_note,
        "status": o.status,
        "accepted_usta_name": o.accepted_usta_name,
        "accepted_usta_phone": o.accepted_usta_phone,
        "accepted_usta_telegram_id": o.accepted_usta_telegram_id,
        "accepted_usta_id": o.accepted_usta_id,
        "rating": o.rating,
        "rating_requested": bool(o.rating_requested),
    }


async def create_order(
    session: AsyncSession,
    *,
    client_tg_id: int,
    client_name: str | None,
    username: str | None,
    phone: str | None,
    service: str,
    section_id: int | None,
    section_kind: str | None,
    problem: str,
    lat: float | None,
    lon: float | None,
    problem_media_json: str | None = None,
    service_address_note: str | None = None,
) -> int:
    o = Order(
        client_tg_id=client_tg_id,
        client_name=client_name,
        username=username,
        phone=phone,
        service=service,
        section_id=section_id,
        section_kind=section_kind,
        problem=problem,
        problem_media_json=problem_media_json,
        lat=lat,
        lon=lon,
        service_address_note=service_address_note,
        status="new",
    )
    session.add(o)
    await session.flush()
    await session.commit()
    return int(o.id)


async def get_order(session: AsyncSession, order_id: int) -> dict | None:
    o = await session.get(Order, order_id)
    return order_to_dict(o) if o else None


async def list_recent_orders(session: AsyncSession, limit: int = 10) -> list[dict]:
    q = await session.execute(
        select(Order).order_by(Order.id.desc()).limit(limit)
    )
    rows = q.scalars().all()
    return [order_to_dict(o) for o in rows]


async def list_orders_by_status(session: AsyncSession, status: str, limit: int = 20) -> list[dict]:
    """Status bo'yicha buyurtmalar ro'yxati (yangi/qabul/tugatilgan)."""
    q = await session.execute(
        select(Order)
        .where(Order.status == status)
        .order_by(Order.id.desc())
        .limit(limit)
    )
    return [order_to_dict(o) for o in q.scalars().all()]


async def count_orders_today(session: AsyncSession) -> int:
    """O'zbekiston kalendari bo'yicha bugun (UTC+5)."""
    start_utc, end_utc = utc_day_bounds_for_today_uz()
    q = await session.execute(
        select(func.count()).select_from(Order).where(
            Order.created_at >= start_utc,
            Order.created_at < end_utc,
        )
    )
    return int(q.scalar_one())


async def count_all_orders(session: AsyncSession) -> int:
    q = await session.execute(select(func.count()).select_from(Order))
    return int(q.scalar_one())


async def set_order_status(session: AsyncSession, order_id: int, status: str) -> bool:
    o = await session.get(Order, order_id)
    if not o:
        return False
    o.status = status
    await session.commit()
    return True


async def try_accept_order_by_usta(
    session: AsyncSession,
    *,
    order_id: int,
    section_usta_id: int,
    actor_telegram_id: int,
) -> tuple[
    Literal["ok", "bad_usta", "bad_order", "bad_section", "race"],
    str | None,
    str | None,
]:
    """Bitta usta qabul qiladi (status=new bo'lsa). Qaytadi: (natija, ism, telefon)."""
    usta = await session.get(SectionUsta, section_usta_id)
    if not usta or usta.telegram_id is None or int(usta.telegram_id) != int(actor_telegram_id):
        return ("bad_usta", None, None)
    order = await session.get(Order, order_id)
    if not order:
        return ("bad_order", None, None)
    if order.section_id is None or int(order.section_id) != int(usta.section_id):
        return ("bad_section", None, None)
    parts = [usta.first_name, usta.last_name or ""]
    name = " ".join(p for p in parts if p).strip() or usta.first_name
    phone = (usta.phone or "").strip()
    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.status == "new")
        .values(
            status="accepted",
            accepted_usta_name=name,
            accepted_usta_phone=phone,
            accepted_usta_telegram_id=int(actor_telegram_id),
            accepted_usta_id=section_usta_id,
        )
    )
    res = await session.execute(stmt)
    await session.commit()
    if res.rowcount == 0:
        return ("race", None, None)
    return ("ok", name, phone)


async def admin_assign_order(
    session: AsyncSession,
    *,
    order_id: int,
    section_usta_id: int,
) -> tuple[str, str | None, str | None]:
    """Admin manually assigns a 'new' order to a specific usta."""
    su = await session.get(SectionUsta, section_usta_id)
    if not su or not su.telegram_id:
        return ("no_usta", None, None)
    name = f"{su.first_name} {su.last_name or ''}".strip()
    phone = (su.phone or su.phone_normalized or "").strip()
    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.status == "new")
        .values(
            status="accepted",
            accepted_usta_name=name,
            accepted_usta_phone=phone,
            accepted_usta_telegram_id=int(su.telegram_id),
            accepted_usta_id=section_usta_id,
        )
    )
    res = await session.execute(stmt)
    await session.commit()
    if res.rowcount == 0:
        return ("race", None, None)
    return ("ok", name, phone)


async def complete_order(
    session: AsyncSession,
    *,
    order_id: int,
    actor_telegram_id: int,
    admin_id: int,
) -> tuple[bool, dict | None]:
    """Mijoz yoki admin buyurtmani yakunlaydi (status=done, rating_requested=True)."""
    order = await session.get(Order, order_id)
    if not order or order.status != "accepted":
        return (False, None)
    # Faqat mijoz yoki admin (usta tugmasi yo'q — yakunlash mijozda)
    if actor_telegram_id != admin_id and int(order.client_tg_id) != int(
        actor_telegram_id
    ):
        return (False, None)
    order.status = "done"
    order.rating_requested = True
    await session.commit()
    return (True, order_to_dict(order))


async def set_order_rating(
    session: AsyncSession,
    *,
    order_id: int,
    client_tg_id: int,
    rating: int,
) -> tuple[bool, dict | None]:
    """Mijoz buyurtmani baholaydi. Faqat bir marta baholanadi."""
    order = await session.get(Order, order_id)
    if not order:
        return (False, None)
    if int(order.client_tg_id) != int(client_tg_id):
        return (False, None)
    if order.rating is not None:
        return (False, order_to_dict(order))
    order.rating = rating
    await session.commit()
    return (True, order_to_dict(order))
