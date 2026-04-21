"""Matn formatlash (admin xabarlari)."""

from aiogram.types import User

from packages.db.repositories.sections import KIND_ADMIN_CONTACT, KIND_SUGGESTION


def display_name_from_user(user: User | None) -> str:
    if not user:
        return "(noma'lum)"
    parts = [user.first_name or "", user.last_name or ""]
    name = " ".join(p for p in parts if p).strip()
    return name if name else "(Telegramda ism yo'q)"


def _detail_label(section_kind: str | None) -> str:
    if section_kind == KIND_SUGGESTION:
        return "Taklif"
    if section_kind == KIND_ADMIN_CONTACT:
        return "Murojaat"
    return "Muammo"


def format_order_detail(row: dict) -> str:
    loc = "Yo'q"
    if row.get("lat") is not None and row.get("lon") is not None:
        lat, lon = row["lat"], row["lon"]
        loc = f"{lat:.6f}, {lon:.6f}\nhttps://maps.google.com/?q={lat},{lon}"
    cid = row["client_tg_id"]
    plabel = _detail_label(row.get("section_kind"))
    un = row.get("username")
    un_line = f"@{un}" if un else "(username yo'q)"
    phone = row.get("phone")
    phone_line = phone if phone else "(telefon berilmagan)"
    tme = f"https://t.me/{un}" if un else "(username bo‘lmasa to‘g‘ridan-to‘g‘ri chat yo‘q)"
    return (
        f"🆔 Buyurtma #{row['id']}\n"
        f"🕐 {row['created_at']}\n"
        f"📌 Status: {row['status']}\n"
        f"👤 Ism: {row.get('client_name') or '—'}\n"
        f"🔗 Username: {un_line}\n"
        f"📞 Telefon: {phone_line}\n"
        f"🆔 TG id: {cid}\n"
        f"💬 Chat: tg://user?id={cid}\n"
        f"🌐 t.me: {tme}\n"
        f"🔧 Xizmat: {row['service']}\n"
        f"📝 {plabel}:\n{row['problem']}\n"
        f"📍 Lokatsiya: {loc}"
    )


def build_admin_notify_user_block(
    user: User | None,
    phone: str | None,
    client_tg_id: int,
    *,
    profile_full_name: str | None = None,
) -> str:
    if profile_full_name and profile_full_name.strip():
        name = profile_full_name.strip()
    elif user and user.full_name and user.full_name.strip():
        name = user.full_name.strip()
    else:
        name = display_name_from_user(user)
    un = f"@{user.username}" if user and user.username else "(username yo'q)"
    ph = phone if phone else "(telefon yo'q)"
    return (
        f"Mijoz (ro'yxat): {name}\n"
        f"Username: {un}\n"
        f"Telefon: {ph}\n"
        f"TG id: {client_tg_id}\n"
        f"Chat: tg://user?id={client_tg_id}"
    )
