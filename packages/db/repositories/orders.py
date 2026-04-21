"""Buyurtmalar."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import Order
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
        "section_kind": o.section_kind,
        "problem": o.problem,
        "lat": o.lat,
        "lon": o.lon,
        "status": o.status,
    }


async def create_order(
    session: AsyncSession,
    *,
    client_tg_id: int,
    client_name: str | None,
    username: str | None,
    phone: str | None,
    service: str,
    section_kind: str | None,
    problem: str,
    lat: float | None,
    lon: float | None,
) -> int:
    o = Order(
        client_tg_id=client_tg_id,
        client_name=client_name,
        username=username,
        phone=phone,
        service=service,
        section_kind=section_kind,
        problem=problem,
        lat=lat,
        lon=lon,
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
