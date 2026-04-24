"""SQLite / PostgreSQL uchun oddiy migratsiyalar (Alembic keyin)."""

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

        r_sec = await conn.execute(text("PRAGMA table_info(sections)"))
        secols = {row[1] for row in r_sec.fetchall()}
        if secols and "usta_telegram_id" not in secols:
            await conn.execute(
                text("ALTER TABLE sections ADD COLUMN usta_telegram_id BIGINT")
            )

        r_ord = await conn.execute(text("PRAGMA table_info(orders)"))
        ocols = {row[1] for row in r_ord.fetchall()}
        if ocols:
            if "section_id" not in ocols:
                await conn.execute(
                    text("ALTER TABLE orders ADD COLUMN section_id INTEGER")
                )
            if "accepted_usta_name" not in ocols:
                await conn.execute(
                    text("ALTER TABLE orders ADD COLUMN accepted_usta_name VARCHAR(256)")
                )
            if "accepted_usta_phone" not in ocols:
                await conn.execute(
                    text("ALTER TABLE orders ADD COLUMN accepted_usta_phone VARCHAR(32)")
                )
            if "accepted_usta_telegram_id" not in ocols:
                await conn.execute(
                    text(
                        "ALTER TABLE orders ADD COLUMN accepted_usta_telegram_id BIGINT"
                    )
                )

        # section_ustas: yangi sxemani tekshir va kerak bo'lsa rebuild qil
        r_su_check = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='section_ustas'"))
        su_exists = r_su_check.fetchone() is not None

        if not su_exists:
            # Yangi o'rnatish — to'g'ridan-to'g'ri yangi sxema
            await conn.execute(
                text(
                    """
                    CREATE TABLE section_ustas (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
                        telegram_id BIGINT,
                        first_name VARCHAR(64) NOT NULL DEFAULT '',
                        last_name VARCHAR(64) NOT NULL DEFAULT '',
                        phone VARCHAR(32) NOT NULL DEFAULT '',
                        phone_normalized VARCHAR(32) NOT NULL DEFAULT '',
                        CONSTRAINT uq_section_usta_phone UNIQUE (section_id, phone_normalized)
                    )
                    """
                )
            )
        else:
            # Mavjud jadval — telegram_id NULL ga ruxsat berilganmi tekshir
            r_su_info = await conn.execute(text("PRAGMA table_info(section_ustas)"))
            su_col_info = {row[1]: row for row in r_su_info.fetchall()}
            tg_col = su_col_info.get("telegram_id")
            needs_rebuild = tg_col is not None and tg_col[3] == 1  # notnull=1

            if needs_rebuild:
                # SQLite ALTER COLUMN ishlamaydi — jadvalni qayta quramiz
                await conn.execute(text("ALTER TABLE section_ustas RENAME TO section_ustas_old"))
                await conn.execute(
                    text(
                        """
                        CREATE TABLE section_ustas (
                            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
                            telegram_id BIGINT,
                            first_name VARCHAR(64) NOT NULL DEFAULT '',
                            last_name VARCHAR(64) NOT NULL DEFAULT '',
                            phone VARCHAR(32) NOT NULL DEFAULT '',
                            phone_normalized VARCHAR(32) NOT NULL DEFAULT '',
                            CONSTRAINT uq_section_usta_phone UNIQUE (section_id, phone_normalized)
                        )
                        """
                    )
                )
                # Eski ma'lumotlarni ko'chirish
                # display_name ustuni bo'lsa first_name ga, aks holda first_name ishlatiladi
                old_has_display = "display_name" in su_col_info
                fn_expr = "COALESCE(NULLIF(first_name,''), display_name, 'Usta')" if old_has_display else "COALESCE(NULLIF(first_name,''), 'Usta')"
                await conn.execute(
                    text(
                        f"""
                        INSERT INTO section_ustas
                            (id, section_id, telegram_id, first_name, last_name, phone, phone_normalized)
                        SELECT
                            id,
                            section_id,
                            telegram_id,
                            {fn_expr},
                            COALESCE(last_name, ''),
                            COALESCE(NULLIF(phone,''), '—'),
                            CASE
                                WHEN phone_normalized IS NOT NULL AND phone_normalized != ''
                                    THEN phone_normalized
                                WHEN phone IS NOT NULL AND phone != ''
                                    THEN REPLACE(REPLACE(REPLACE(phone,'+',''),' ',''),'-','')
                                ELSE CAST(id AS TEXT)
                            END
                        FROM section_ustas_old
                        """
                    )
                )
                await conn.execute(text("DROP TABLE section_ustas_old"))
                await conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_section_ustas_section_id ON section_ustas (section_id)")
                )
                await conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_section_ustas_telegram_id ON section_ustas (telegram_id)")
                )
            else:
                # Ustunlar bor-yo'qligini tekshir, kerak bo'lsa qo'sh
                su_cols = set(su_col_info.keys())
                if "first_name" not in su_cols:
                    await conn.execute(
                        text("ALTER TABLE section_ustas ADD COLUMN first_name VARCHAR(64) NOT NULL DEFAULT ''")
                    )
                if "last_name" not in su_cols:
                    await conn.execute(
                        text("ALTER TABLE section_ustas ADD COLUMN last_name VARCHAR(64) NOT NULL DEFAULT ''")
                    )
                if "phone_normalized" not in su_cols:
                    await conn.execute(
                        text("ALTER TABLE section_ustas ADD COLUMN phone_normalized VARCHAR(32) NOT NULL DEFAULT ''")
                    )
                if "display_name" in su_cols:
                    await conn.execute(
                        text(
                            "UPDATE section_ustas SET first_name = display_name WHERE first_name = '' AND display_name != ''"
                        )
                    )

        # Mavjud qatorlar uchun phone_normalized ni to'ldirish
        await conn.execute(
            text(
                """
                UPDATE section_ustas
                SET phone_normalized = CASE
                    WHEN LENGTH(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                        phone, '+', ''), ' ', ''), '-', ''), '(', ''), ')', ''), '\t', '')) = 9
                    THEN '998' || REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                        phone, '+', ''), ' ', ''), '-', ''), '(', ''), ')', ''), '\t', '')
                    WHEN LENGTH(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                        phone, '+', ''), ' ', ''), '-', ''), '(', ''), ')', ''), '\t', '')) = 12
                    THEN REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                        phone, '+', ''), ' ', ''), '-', ''), '(', ''), ')', ''), '\t', '')
                    ELSE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                        phone, '+', ''), ' ', ''), '-', ''), '(', ''), ')', ''), '\t', '')
                END
                WHERE phone_normalized = ''
                """
            )
        )

        # Eski section_ustas.telegram_id NULL bo'lmagan qatorlari uchun seeding (agar oldin NULL emas edi)
        await conn.execute(
            text(
                """
                INSERT INTO section_ustas (section_id, telegram_id, first_name, last_name, phone, phone_normalized)
                SELECT s.id, s.usta_telegram_id, 'Usta', '', '—', ''
                FROM sections s
                WHERE s.usta_telegram_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM section_ustas u
                      WHERE u.section_id = s.id AND u.telegram_id = s.usta_telegram_id
                  )
                """
            )
        )

        # Reyting ustunlari (section_ustas)
        r_su2 = await conn.execute(text("PRAGMA table_info(section_ustas)"))
        su_cols2 = {row[1] for row in r_su2.fetchall()}
        if "rating_sum" not in su_cols2:
            await conn.execute(
                text("ALTER TABLE section_ustas ADD COLUMN rating_sum REAL NOT NULL DEFAULT 0.0")
            )
        if "rating_count" not in su_cols2:
            await conn.execute(
                text("ALTER TABLE section_ustas ADD COLUMN rating_count INTEGER NOT NULL DEFAULT 0")
            )

        # Reyting + usta_id ustunlari (orders)
        r_ord2 = await conn.execute(text("PRAGMA table_info(orders)"))
        ord_cols2 = {row[1] for row in r_ord2.fetchall()}
        if "accepted_usta_id" not in ord_cols2:
            await conn.execute(
                text("ALTER TABLE orders ADD COLUMN accepted_usta_id INTEGER")
            )
        if "rating" not in ord_cols2:
            await conn.execute(
                text("ALTER TABLE orders ADD COLUMN rating INTEGER")
            )
        if "rating_requested" not in ord_cols2:
            await conn.execute(
                text("ALTER TABLE orders ADD COLUMN rating_requested INTEGER NOT NULL DEFAULT 0")
            )


async def run_postgres_migrations(engine: AsyncEngine) -> None:
    """Mavjud PostgreSQL jadvaliga yangi ustunlar (create_all eski DB ni yangilamaydi)."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE sections ADD COLUMN IF NOT EXISTS usta_telegram_id BIGINT"
            )
        )
        await conn.execute(
            text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS section_id INTEGER")
        )
        await conn.execute(
            text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS accepted_usta_name VARCHAR(256)"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS accepted_usta_phone VARCHAR(32)"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS accepted_usta_telegram_id BIGINT"
            )
        )
        # Yangi sxema bilan jadval
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS section_ustas (
                    id SERIAL PRIMARY KEY,
                    section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
                    telegram_id BIGINT,
                    first_name VARCHAR(64) NOT NULL DEFAULT '',
                    last_name VARCHAR(64) NOT NULL DEFAULT '',
                    phone VARCHAR(32) NOT NULL DEFAULT '',
                    phone_normalized VARCHAR(32) NOT NULL DEFAULT '',
                    CONSTRAINT uq_section_usta_phone UNIQUE (section_id, phone_normalized)
                )
                """
            )
        )
        # Eski sxemadan (display_name, telegram_id NOT NULL) yangi sxemaga o'tish
        for col_def in [
            ("first_name", "VARCHAR(64) NOT NULL DEFAULT ''"),
            ("last_name", "VARCHAR(64) NOT NULL DEFAULT ''"),
            ("phone_normalized", "VARCHAR(32) NOT NULL DEFAULT ''"),
        ]:
            await conn.execute(
                text(
                    f"ALTER TABLE section_ustas ADD COLUMN IF NOT EXISTS {col_def[0]} {col_def[1]}"
                )
            )
        # display_name ni first_name ga ko'chirish
        await conn.execute(
            text(
                """
                UPDATE section_ustas
                SET first_name = display_name
                WHERE first_name = '' AND display_name IS NOT NULL AND display_name != ''
                """
            )
        )
        # phone_normalized to'ldirish
        await conn.execute(
            text(
                """
                UPDATE section_ustas
                SET phone_normalized = regexp_replace(phone, '[^0-9]', '', 'g')
                WHERE phone_normalized = ''
                """
            )
        )
        # telegram_id NULL ga ruxsat — eski NOT NULL cheklov yo'q qilish (agar mavjud jadval)
        # PostgreSQL da ALTER COLUMN DROP NOT NULL xavfsiz
        try:
            await conn.execute(
                text("ALTER TABLE section_ustas ALTER COLUMN telegram_id DROP NOT NULL")
            )
        except Exception:
            pass
        # unique constraint eski nomi bilan bo'lsa olib tashlash
        try:
            await conn.execute(
                text(
                    "ALTER TABLE section_ustas DROP CONSTRAINT IF EXISTS uq_section_usta_telegram"
                )
            )
        except Exception:
            pass
        # yangi unique constraint qo'shish
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'uq_section_usta_phone'
                    ) THEN
                        ALTER TABLE section_ustas
                        ADD CONSTRAINT uq_section_usta_phone UNIQUE (section_id, phone_normalized);
                    END IF;
                END $$;
                """
            )
        )
        # Partial unique index: bir usta bir bo'limda faqat bir marta (telegram_id IS NOT NULL)
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_section_usta_tg_claimed
                ON section_ustas (section_id, telegram_id)
                WHERE telegram_id IS NOT NULL
                """
            )
        )
        # Seeding: eski sections.usta_telegram_id dan
        await conn.execute(
            text(
                """
                INSERT INTO section_ustas (section_id, telegram_id, first_name, last_name, phone, phone_normalized)
                SELECT s.id, s.usta_telegram_id, 'Usta', '', '—', ''
                FROM sections s
                WHERE s.usta_telegram_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM section_ustas u
                      WHERE u.section_id = s.id AND u.telegram_id = s.usta_telegram_id
                  )
                ON CONFLICT DO NOTHING
                """
            )
        )
        # Reyting ustunlari (section_ustas)
        for col_def in [
            ("rating_sum", "FLOAT NOT NULL DEFAULT 0.0"),
            ("rating_count", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            await conn.execute(
                text(
                    f"ALTER TABLE section_ustas ADD COLUMN IF NOT EXISTS {col_def[0]} {col_def[1]}"
                )
            )
        # Reyting + usta_id ustunlari (orders)
        for col_def in [
            ("accepted_usta_id", "INTEGER"),
            ("rating", "INTEGER"),
            ("rating_requested", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ]:
            await conn.execute(
                text(
                    f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col_def[0]} {col_def[1]}"
                )
            )
