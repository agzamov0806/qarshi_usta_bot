"""
Eski SQLite (data/app.db) dan PostgreSQL ga ma'lumotlarni ko'chirish.

Talab: .env da DATABASE_URL=postgresql+asyncpg://...

  docker compose up -d
  python scripts/migrate_sqlite_to_postgres.py

Ixtiyoriy: SQLITE_SOURCE=boshqa/yo'l.db
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import delete, inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from packages.db.models import Base, Order, Section, SectionUsta, User
from shared.config import clear_settings_cache, get_settings


def _columns_dict(obj: Any) -> dict[str, Any]:
    return {
        attr.key: getattr(obj, attr.key)
        for attr in inspect(obj).mapper.column_attrs
    }


async def _main() -> None:
    clear_settings_cache()
    settings = get_settings()
    pg_url = settings.database_url
    if "postgres" not in pg_url.lower():
        print("DATABASE_URL PostgreSQL bo'lishi kerak (postgresql+asyncpg://...).")
        raise SystemExit(1)

    sqlite_path = Path(os.environ.get("SQLITE_SOURCE", "data/app.db"))
    if not sqlite_path.is_absolute():
        sqlite_path = _ROOT / sqlite_path
    if not sqlite_path.exists():
        print("SQLite fayl topilmadi:", sqlite_path)
        raise SystemExit(1)

    sqlite_url = f"sqlite+aiosqlite:///{sqlite_path.as_posix()}"
    sqlite_engine = create_async_engine(sqlite_url)
    pg_engine = create_async_engine(
        pg_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )

    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SqliteSession = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    async with SqliteSession() as ss:
        users = (await ss.execute(select(User))).scalars().all()
        sections = (await ss.execute(select(Section))).scalars().all()
        orders = (await ss.execute(select(Order))).scalars().all()

    user_rows = [_columns_dict(u) for u in users]
    section_rows = [_columns_dict(s) for s in sections]
    order_rows: list[dict[str, Any]] = []
    for o in orders:
        d = _columns_dict(o)
        d.setdefault("section_id", None)
        d.setdefault("accepted_usta_name", None)
        d.setdefault("accepted_usta_phone", None)
        d.setdefault("accepted_usta_telegram_id", None)
        order_rows.append(d)

    section_ustas_seed: list[dict[str, Any]] = []
    try:
        async with SqliteSession() as ss2:
            su_list = (await ss2.execute(select(SectionUsta))).scalars().all()
        for su in su_list:
            d = _columns_dict(su)
            d.setdefault("first_name", d.pop("display_name", "") or "")
            d.setdefault("last_name", "")
            d.setdefault("phone_normalized", "")
            d.setdefault("telegram_id", None)
            section_ustas_seed.append(d)
    except Exception as exc:
        print(f"section_ustas o'qishda xato (eski sxema?): {exc}")
        # Eski sxemadan seeding: sections.usta_telegram_id
        for s in sections:
            cols = _columns_dict(s)
            tid = cols.get("usta_telegram_id")
            if tid is not None:
                section_ustas_seed.append({
                    "section_id": int(s.id),
                    "telegram_id": int(tid),
                    "first_name": "Usta",
                    "last_name": "",
                    "phone": "—",
                    "phone_normalized": "",
                })

    print(
        f"SQLite: users={len(user_rows)} sections={len(section_rows)} "
        f"orders={len(order_rows)} section_ustas_seed={len(section_ustas_seed)}"
    )

    PgSession = async_sessionmaker(pg_engine, expire_on_commit=False)
    async with PgSession() as session:
        async with session.begin():
            await session.execute(delete(Order))
            await session.execute(delete(SectionUsta))
            await session.execute(delete(Section))
            await session.execute(delete(User))
            for row in user_rows:
                session.add(User(**row))
            for row in section_rows:
                session.add(Section(**row))
            for row in section_ustas_seed:
                row.pop("display_name", None)
                session.add(SectionUsta(**row))
            for row in order_rows:
                session.add(Order(**row))

    max_sid = max((r["id"] for r in section_rows), default=0)
    max_oid = max((r["id"] for r in order_rows), default=0)

    async with PgSession() as session:
        r = await session.execute(
            select(SectionUsta.id).order_by(SectionUsta.id.desc()).limit(1)
        )
        max_uid_row = r.scalar_one_or_none()
    max_uid = int(max_uid_row) if max_uid_row else 0

    async with PgSession() as session:
        async with session.begin():
            await session.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('sections', 'id'), :mx, :called)"
                ),
                {"mx": max_sid if max_sid else 1, "called": bool(max_sid)},
            )
            await session.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('orders', 'id'), :mx, :called)"
                ),
                {"mx": max_oid if max_oid else 1, "called": bool(max_oid)},
            )
            if max_uid:
                await session.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence('section_ustas', 'id'), :mx, true)"
                    ),
                    {"mx": max_uid},
                )

    await sqlite_engine.dispose()
    await pg_engine.dispose()
    print("Ko'chirish yakunlandi.")


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        print(
            "PostgreSQL ga ulanib bo'lmadi. Avval loyiha ildizida: docker compose up -d",
            f"({e!r})",
        )
        raise SystemExit(1) from e
