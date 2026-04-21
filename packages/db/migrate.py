"""SQLite uchun oddiy migratsiyalar (Alembic keyin)."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def run_sqlite_migrations(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        r = await conn.execute(text("PRAGMA table_info(orders)"))
        cols = {row[1] for row in r.fetchall()}
        if cols and "section_kind" not in cols:
            await conn.execute(
                text("ALTER TABLE orders ADD COLUMN section_kind VARCHAR(32)")
            )

        r_u = await conn.execute(text("PRAGMA table_info(users)"))
        ucols = {row[1] for row in r_u.fetchall()}
        if ucols and "locale" not in ucols:
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN locale VARCHAR(8) DEFAULT 'uz'")
            )
