"""Async engine va sessiya.

Barcha handlerlar asyncio event loopda ishlaydi; har bir so‘rov odatda
alohida AsyncSession bilan DB ga ulanadi (parallel ishga mos).

SQLite: parallel o‘qish/yozish uchun WAL + busy_timeout (DATABASE_URL da sqlite bo‘lsa).
Standart muhit: PostgreSQL (asyncpg). Minglab yozuv: prod uchun Postgres tavsiya etiladi.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from packages.db.models import Base
from shared.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _apply_sqlite_pragmas(engine: AsyncEngine) -> None:
    """Har bir yangi ulanishda WAL va kutish — concurrent mijozlarda qotmaslik."""

    @sa.event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record) -> None:  # type: ignore[no-untyped-def]
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url = (settings.database_url or "").lower()
        kwargs: dict = {"echo": False}

        if "sqlite" in url:
            Path("data").mkdir(parents=True, exist_ok=True)
            # Qulf kutishi (soniya); parallel handlerlar uchun
            kwargs["connect_args"] = {"timeout": 30.0}
        elif "postgres" in url:
            kwargs["pool_pre_ping"] = True
            kwargs["pool_size"] = 20
            kwargs["max_overflow"] = 15

        _engine = create_async_engine(settings.database_url, **kwargs)

        if "sqlite" in url:
            _apply_sqlite_pragmas(_engine)

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    if "sqlite" in settings.database_url:
        from packages.db.migrate import run_sqlite_migrations

        await run_sqlite_migrations(engine)
    elif "postgres" in settings.database_url.lower():
        from packages.db.migrate import run_postgres_migrations

        await run_postgres_migrations(engine)

    from packages.db.repositories import sections as sections_repo

    async with get_session_factory()() as session:
        await sections_repo.seed_defaults_if_empty(session)


async def close_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
