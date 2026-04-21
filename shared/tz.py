"""O'zbekiston vaqti (doimiy UTC+5, DST yo'q)."""

from datetime import datetime, timedelta, timezone

# Asia/Tashkent bilan bir xil offset; Windowsda zoneinfo/tzdata muammosiz
UZ = timezone(timedelta(hours=5), name="UTC+5")


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_dt_uz(dt: datetime | None) -> str:
    if not dt:
        return ""
    local = ensure_utc(dt).astimezone(UZ)
    return local.strftime("%Y-%m-%d %H:%M") + " (UTC+5)"


def utc_day_bounds_for_today_uz() -> tuple[datetime, datetime]:
    """Bugungi kun (UTC+5 kalendari) — chegaralar UTC da (DB bilan solishtirish)."""
    now_uz = datetime.now(UZ)
    start_uz = now_uz.replace(hour=0, minute=0, second=0, microsecond=0)
    end_uz = start_uz + timedelta(days=1)
    return (
        start_uz.astimezone(timezone.utc),
        end_uz.astimezone(timezone.utc),
    )
