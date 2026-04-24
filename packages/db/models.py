"""SQLAlchemy modellar."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str] = mapped_column(String(32))
    # uz | ru — interfeys tili
    locale: Mapped[str] = mapped_column(String(8), default="uz")
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Section(Base):
    """Xizmat bo'limlari (admin CRUD)."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), unique=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    # standard | suggestion | admin_contact
    kind: Mapped[str] = mapped_column(String(32), default="standard")
    # Bo'lim bo'yicha usta (Telegram chat id); admin biriktiradi
    usta_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class SectionUsta(Base):
    """Bo'lim bo'yicha usta (bir nechta); admin qo'shadi, usta /start orqali bog'lanadi."""

    __tablename__ = "section_ustas"
    __table_args__ = (
        # telefon bo'yicha bir bo'limda takror bo'lmasin
        UniqueConstraint("section_id", "phone", name="uq_section_usta_phone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"),
        index=True,
    )
    # NULL = admin qo'shgan, lekin usta hali /start bilan bog'lanmagan
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[str] = mapped_column(String(64), default="")
    phone: Mapped[str] = mapped_column(String(32))
    # normalized phone (matching uchun); avtomatik hisoblanadi
    phone_normalized: Mapped[str] = mapped_column(String(32), default="")
    # Reyting: barcha baholар yig'indisi va soni
    rating_sum: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(default=0)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    client_tg_id: Mapped[int] = mapped_column(BigInteger)
    client_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    service: Mapped[str] = mapped_column(String(256))
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    section_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    problem: Mapped[str] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="new")
    accepted_usta_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    accepted_usta_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accepted_usta_telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    # Qaysi SectionUsta qabul qildi (baholash uchun)
    accepted_usta_id: Mapped[int | None] = mapped_column(nullable=True)
    # Mijozdan baho (1-5); NULL = berilmagan
    rating: Mapped[int | None] = mapped_column(nullable=True)
    # Mijozga baholash so'rovi yuborilganmi
    rating_requested: Mapped[bool] = mapped_column(default=False)
