"""Admin: bo'limlar CRUD (Telegram)."""

from html import escape

from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from packages.db.repositories import section_ustas as section_ustas_repo
from packages.db.repositories import sections as sections_repo
from packages.db.repositories.sections import (
    KIND_ADMIN_CONTACT,
    KIND_LABELS,
    KIND_STANDARD,
    KIND_SUGGESTION,
)
from packages.db.session import get_session_factory
from services.bot.callback_data import (
    AdminCallback,
    SectionCallback,
    SectionKindCallback,
    SectionUstaCallback,
)
from services.bot.router import router
from services.bot.states import SectionAdminStates
from shared.config import get_settings
from shared.phone_norm import format_phone_display, normalize_phone_for_storage
from sqlalchemy.exc import IntegrityError

settings = get_settings()
ADMIN_ID = settings.admin_chat_id


def _is_admin(uid: int | None) -> bool:
    return uid is not None and uid == ADMIN_ID


def _usta_suffix(r: dict) -> str:
    n = int(r.get("usta_count") or 0)
    if n > 0:
        return f" · 👷 {n} ta usta"
    return ""


async def _sections_root_text(session) -> str:
    rows = await sections_repo.list_all(session)
    lines = ["📂 <b>Bo'limlar boshqaruvi</b>\n"]
    if not rows:
        lines.append("Hozircha bo'lim yo'q. «➕ Qo'shish»dan boshlang.")
    else:
        for r in rows:
            st = "✅" if r["is_active"] else "⏸"
            lines.append(
                f"{r['id']}. {st} <b>{escape(r['title'])}</b>{_usta_suffix(r)}\n   "
                f"Tur: {KIND_LABELS.get(r['kind'], r['kind'])}"
            )
    return "\n".join(lines)


def _sections_root_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Qo'shish",
                    callback_data=SectionCallback(action="add", sid=0).pack(),
                ),
                InlineKeyboardButton(
                    text="🔄 Ro'yxat",
                    callback_data=SectionCallback(action="list", sid=0).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Admin bosh sahifa",
                    callback_data=AdminCallback(action="menu").pack(),
                )
            ],
        ]
    )


def _usta_row_label(r: dict) -> str:
    name = escape(r["display_name"])
    phone = format_phone_display(r["phone"])
    if r["claimed"]:
        return f"✅ {name} {phone}"
    return f"⌛ {name} {phone}"


def _section_ustas_message_html(title: str, sid: int, rows: list[dict], bot_username: str = "") -> str:
    lines = [f"👷 <b>{escape(title)}</b> (№{sid}) — <b>ustalar</b>\n"]
    if not rows:
        lines.append("Hozircha usta qo'shilmagan. «➕ Usta qo'shish».")
    else:
        for r in rows:
            name = escape(r["display_name"])
            phone = format_phone_display(r["phone"])
            status = "✅ bog'langan" if r["claimed"] else "⌛ kutilmoqda"
            lines.append(f"· <b>{name}</b> — {phone} — {status}")
    if bot_username:
        link = f"https://t.me/{bot_username}?start=usta"
        lines.append(f"\n📲 Usta uchun havola: {link}")
    lines.append(
        "\n<i>⌛ — usta hali botda /start bilan bog'lanmagan.\n"
        "✅ — usta bog'langan, buyurtma keladi.</i>"
    )
    return "\n".join(lines)


def _section_ustas_kb(sid: int, rows: list[dict]) -> InlineKeyboardMarkup:
    btns: list[list[InlineKeyboardButton]] = []
    for r in rows:
        label = _usta_row_label(r)
        short = label[:28] + ("…" if len(label) > 28 else "")
        btns.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {short}",
                    callback_data=SectionUstaCallback(
                        action="del", sid=sid, uid=int(r["id"])
                    ).pack(),
                )
            ]
        )
    btns.append(
        [
            InlineKeyboardButton(
                text="➕ Usta qo'shish",
                callback_data=SectionUstaCallback(action="add", sid=sid).pack(),
            ),
            InlineKeyboardButton(
                text="◀️",
                callback_data=SectionCallback(action="list", sid=0).pack(),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=btns)


def _section_row_kb(sid: int) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text="✏️",
            callback_data=SectionCallback(action="edit", sid=sid).pack(),
        ),
        InlineKeyboardButton(
            text="🏷 Tur",
            callback_data=SectionCallback(action="kind", sid=sid).pack(),
        ),
        InlineKeyboardButton(
            text="👤 Usta",
            callback_data=SectionCallback(action="usta", sid=sid).pack(),
        ),
        InlineKeyboardButton(
            text="⏯",
            callback_data=SectionCallback(action="toggle", sid=sid).pack(),
        ),
        InlineKeyboardButton(
            text="🗑",
            callback_data=SectionCallback(action="del", sid=sid).pack(),
        ),
    ]


@router.callback_query(AdminCallback.filter(F.action == "sections"), F.from_user.id == ADMIN_ID)
async def cb_open_sections(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        txt = await _sections_root_text(session)
    await call.message.edit_text(
        txt,
        reply_markup=_sections_root_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(SectionCallback.filter(F.action == "list"), F.from_user.id == ADMIN_ID)
async def cb_section_list(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        rows = await sections_repo.list_all(session)
    if not rows:
        await call.answer("Bo'lim yo'q", show_alert=True)
        return
    lines = ["<b>Barcha bo'limlar</b>\n"]
    kb: list[list[InlineKeyboardButton]] = []
    for r in rows:
        st = "✅" if r["is_active"] else "⏸"
        lines.append(f"{st} #{r['id']} — {escape(r['title'])}{_usta_suffix(r)}")
        kb.append(_section_row_kb(r["id"]))
    kb.append(
        [
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data=SectionCallback(action="menu", sid=0).pack(),
            )
        ]
    )
    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(SectionCallback.filter(F.action == "menu"), F.from_user.id == ADMIN_ID)
async def cb_section_menu(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        txt = await _sections_root_text(session)
    await call.message.edit_text(
        txt,
        reply_markup=_sections_root_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(SectionCallback.filter(F.action == "add"), F.from_user.id == ADMIN_ID)
async def cb_section_add(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SectionAdminStates.waiting_new_title)
    await call.message.answer(
        "➕ <b>Yangi bo'lim</b>\n\n"
        "Nomini yozing: <b>1–64 belgi</b>, boshqa bo'limda yo'q bo'lsin.\n"
        "/cancel — bekor qilish.",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(SectionAdminStates.waiting_new_title, F.text)
async def msg_section_new_title(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    t = (message.text or "").strip()
    if len(t) < 1 or len(t) > 64:
        await message.answer("1–64 belgi orasida yozing.")
        return
    async with get_session_factory()() as session:
        try:
            await sections_repo.create_section(session, title=t, kind=KIND_STANDARD)
        except IntegrityError:
            await session.rollback()
            await message.answer("Bu nom allaqachon bor. Boshqa nom tanlang.")
            return
    await state.clear()
    await message.answer(
        f"✅ Qo'shildi: <b>{t}</b>",
        parse_mode="HTML",
    )
    async with get_session_factory()() as session:
        txt = await _sections_root_text(session)
    await message.answer(
        txt,
        reply_markup=_sections_root_kb(),
        parse_mode="HTML",
    )


@router.callback_query(SectionCallback.filter(F.action == "edit"), F.from_user.id == ADMIN_ID)
async def cb_section_edit(call: CallbackQuery, callback_data: SectionCallback, state: FSMContext) -> None:
    await state.set_state(SectionAdminStates.waiting_edit_title)
    await state.update_data(edit_sid=callback_data.sid)
    await call.message.answer(
        f"✏️ Bo'lim #{callback_data.sid} uchun <b>yangi nom</b> yozing (1–64 belgi).",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(SectionAdminStates.waiting_edit_title, F.text)
async def msg_section_edit_title(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    data = await state.get_data()
    sid = data.get("edit_sid")
    if not sid:
        await state.clear()
        return
    t = (message.text or "").strip()
    if len(t) < 1 or len(t) > 64:
        await message.answer("1–64 belgi orasida yozing.")
        return
    async with get_session_factory()() as session:
        try:
            ok = await sections_repo.update_section(session, sid, title=t)
        except IntegrityError:
            await session.rollback()
            await message.answer("Bu nom band. Boshqa nom tanlang.")
            return
    await state.clear()
    if ok:
        await message.answer("✅ Saqlandi.")
    else:
        await message.answer("Topilmadi.")


# ---- USTA USTASI EKRANI ----

@router.callback_query(SectionCallback.filter(F.action == "usta"), F.from_user.id == ADMIN_ID)
async def cb_section_usta(call: CallbackQuery, callback_data: SectionCallback) -> None:
    sid = callback_data.sid
    bot_username = (await call.bot.get_me()).username or ""
    async with get_session_factory()() as session:
        s = await sections_repo.get_by_id(session, sid)
        if not s:
            await call.answer("Topilmadi", show_alert=True)
            return
        title = s.title
        rows = await section_ustas_repo.list_for_section(session, sid)
    await call.message.edit_text(
        _section_ustas_message_html(title, sid, rows, bot_username),
        reply_markup=_section_ustas_kb(sid, rows),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(SectionUstaCallback.filter(F.action == "add"), F.from_user.id == ADMIN_ID)
async def cb_section_usta_add(
    call: CallbackQuery, callback_data: SectionUstaCallback, state: FSMContext
) -> None:
    await state.set_state(SectionAdminStates.waiting_usta_first_name)
    await state.update_data(usta_add_sid=callback_data.sid)
    await call.message.answer(
        "➕ <b>Yangi usta</b> — 1/3\n"
        "<b>Ismi</b> (masalan: Jasur)\n"
        "/cancel",
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(SectionUstaCallback.filter(F.action == "del"), F.from_user.id == ADMIN_ID)
async def cb_section_usta_del(
    call: CallbackQuery, callback_data: SectionUstaCallback
) -> None:
    uid = callback_data.uid
    sid = callback_data.sid
    bot_username = (await call.bot.get_me()).username or ""
    async with get_session_factory()() as session:
        u_row = await section_ustas_repo.get_by_id(session, uid)
        if not u_row or int(u_row.section_id) != int(sid):
            await call.answer("Topilmadi", show_alert=True)
            return
        s = await sections_repo.get_by_id(session, sid)
        title = s.title if s else "?"
        await section_ustas_repo.delete_usta(session, uid)
        rows = await section_ustas_repo.list_for_section(session, sid)
    await call.message.edit_text(
        _section_ustas_message_html(title, sid, rows, bot_username),
        reply_markup=_section_ustas_kb(sid, rows),
        parse_mode="HTML",
    )
    await call.answer("O'chirildi")


# ---- USTA QO'SHISH: 3 QADAM (ism → familiya → telefon) ----

@router.message(SectionAdminStates.waiting_usta_first_name, F.text)
async def msg_usta_first_name(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 64:
        await message.answer("Ism 2–64 belgi orasida bo'lsin.")
        return
    await state.update_data(usta_first=name)
    await state.set_state(SectionAdminStates.waiting_usta_last_name)
    await message.answer(
        "2/3 — Usta <b>familiyasi</b> (masalan: Toshmatov)\n/cancel",
        parse_mode="HTML",
    )


@router.message(SectionAdminStates.waiting_usta_last_name, F.text)
async def msg_usta_last_name(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    data = await state.get_data()
    if not data.get("usta_add_sid"):
        await state.clear()
        return
    fam = (message.text or "").strip()
    if len(fam) < 2 or len(fam) > 64:
        await message.answer("Familiya 2–64 belgi orasida bo'lsin.")
        return
    await state.update_data(usta_last=fam)
    await state.set_state(SectionAdminStates.waiting_usta_phone)
    await message.answer(
        "3/3 — Usta <b>telefon raqami</b> (masalan: +998901234567)\n"
        "Bu raqam ustaning Telegram akkauntiga bog'liq bo'lishi kerak.\n"
        "/cancel",
        parse_mode="HTML",
    )


@router.message(SectionAdminStates.waiting_usta_phone, F.text)
async def msg_usta_phone(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    data = await state.get_data()
    sid = data.get("usta_add_sid")
    first = data.get("usta_first", "").strip()
    last = data.get("usta_last", "").strip()
    if not sid or not first:
        await state.clear()
        return
    phone_raw = (message.text or "").strip()
    digits = "".join(c for c in phone_raw if c.isdigit())
    if len(digits) < 9 or len(phone_raw) > 32:
        await message.answer("Telefon juda qisqa yoki juda uzun (9+ raqam).")
        return
    pn = normalize_phone_for_storage(phone_raw)
    async with get_session_factory()() as session:
        try:
            await section_ustas_repo.add_pending_usta(
                session,
                section_id=int(sid),
                first_name=first,
                last_name=last,
                phone=phone_raw,
            )
        except IntegrityError:
            await session.rollback()
            await message.answer(
                "Bu telefon raqam ushbu bo'limda allaqachon qo'shilgan."
            )
            return
    await state.clear()
    bot_username = (await message.bot.get_me()).username or ""
    link = f"https://t.me/{bot_username}?start=usta" if bot_username else ""
    await message.answer(
        f"✅ Usta qo'shildi: <b>{escape(first)} {escape(last)}</b> — "
        f"{format_phone_display(phone_raw)}\n\n"
        f"⌛ Usta hali bog'lanmagan.\n"
        + (f"📲 Shu havolani ustaga yuboring:\n{link}" if link else ""),
        parse_mode="HTML",
    )
    async with get_session_factory()() as session:
        s = await sections_repo.get_by_id(session, int(sid))
        title = s.title if s else "?"
        rows = await section_ustas_repo.list_for_section(session, int(sid))
    await message.answer(
        _section_ustas_message_html(title, int(sid), rows, bot_username),
        reply_markup=_section_ustas_kb(int(sid), rows),
        parse_mode="HTML",
    )


# ---- BO'LIM TUR ----

@router.callback_query(SectionCallback.filter(F.action == "kind"), F.from_user.id == ADMIN_ID)
async def cb_section_kind_menu(call: CallbackQuery, callback_data: SectionCallback) -> None:
    sid = callback_data.sid
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Oddiy buyurtma",
                    callback_data=SectionKindCallback(
                        sid=sid, kind=KIND_STANDARD
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Taklif",
                    callback_data=SectionKindCallback(
                        sid=sid, kind=KIND_SUGGESTION
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Adminga murojaat",
                    callback_data=SectionKindCallback(
                        sid=sid, kind=KIND_ADMIN_CONTACT
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️",
                    callback_data=SectionCallback(action="list", sid=0).pack(),
                )
            ],
        ]
    )
    await call.message.edit_text(
        f"🏷 Bo'lim #{sid} — <b>turini</b> tanlang:",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(SectionKindCallback.filter(), F.from_user.id == ADMIN_ID)
async def cb_section_set_kind(
    call: CallbackQuery, callback_data: SectionKindCallback
) -> None:
    async with get_session_factory()() as session:
        ok = await sections_repo.update_section(
            session, callback_data.sid, kind=callback_data.kind
        )
    await call.answer("Saqlandi" if ok else "Xato", show_alert=True)
    if ok:
        async with get_session_factory()() as session:
            rows = await sections_repo.list_all(session)
        lines = ["<b>Barcha bo'limlar</b>\n"]
        kb: list[list[InlineKeyboardButton]] = []
        for r in rows:
            st = "✅" if r["is_active"] else "⏸"
            lines.append(f"{st} #{r['id']} — {escape(r['title'])}{_usta_suffix(r)}")
            kb.append(_section_row_kb(r["id"]))
        kb.append(
            [
                InlineKeyboardButton(
                    text="◀️ Orqaga",
                    callback_data=SectionCallback(action="menu", sid=0).pack(),
                )
            ]
        )
        await call.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode="HTML",
        )


@router.callback_query(SectionCallback.filter(F.action == "toggle"), F.from_user.id == ADMIN_ID)
async def cb_section_toggle(call: CallbackQuery, callback_data: SectionCallback) -> None:
    async with get_session_factory()() as session:
        s = await sections_repo.get_by_id(session, callback_data.sid)
        if not s:
            await call.answer("Topilmadi", show_alert=True)
            return
        new_val = not s.is_active
        await sections_repo.update_section(
            session, callback_data.sid, is_active=new_val
        )
    await call.answer("Yangilandi", show_alert=False)
    async with get_session_factory()() as session:
        rows = await sections_repo.list_all(session)
    lines = ["<b>Barcha bo'limlar</b>\n"]
    kb: list[list[InlineKeyboardButton]] = []
    for r in rows:
        st = "✅" if r["is_active"] else "⏸"
        lines.append(f"{st} #{r['id']} — {escape(r['title'])}{_usta_suffix(r)}")
        kb.append(_section_row_kb(r["id"]))
    kb.append(
        [
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data=SectionCallback(action="menu", sid=0).pack(),
            )
        ]
    )
    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML",
    )


@router.callback_query(SectionCallback.filter(F.action == "del"), F.from_user.id == ADMIN_ID)
async def cb_section_del_confirm(call: CallbackQuery, callback_data: SectionCallback) -> None:
    sid = callback_data.sid
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, o'chirish",
                    callback_data=SectionCallback(action="dely", sid=sid).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Yo'q",
                    callback_data=SectionCallback(action="list", sid=0).pack(),
                ),
            ],
        ]
    )
    await call.message.edit_text(
        f"🗑 Bo'lim #{sid} o'chirilsinmi?",
        reply_markup=kb,
    )
    await call.answer()


@router.callback_query(SectionCallback.filter(F.action == "dely"), F.from_user.id == ADMIN_ID)
async def cb_section_del_do(call: CallbackQuery, callback_data: SectionCallback) -> None:
    async with get_session_factory()() as session:
        ok = await sections_repo.delete_section(session, callback_data.sid)
    await call.answer("O'chirildi" if ok else "Xato", show_alert=True)
    async with get_session_factory()() as session:
        txt = await _sections_root_text(session)
    await call.message.edit_text(
        txt,
        reply_markup=_sections_root_kb(),
        parse_mode="HTML",
    )


# ---- /cancel ----

@router.message(Command("cancel"), SectionAdminStates.waiting_new_title)
async def cancel_section_new(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    await state.clear()
    await message.answer("Bekor qilindi.")


@router.message(Command("cancel"), SectionAdminStates.waiting_edit_title)
async def cancel_section_edit(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    await state.clear()
    await message.answer("Bekor qilindi.")


@router.message(
    Command("cancel"),
    StateFilter(
        SectionAdminStates.waiting_usta_first_name,
        SectionAdminStates.waiting_usta_last_name,
        SectionAdminStates.waiting_usta_phone,
    ),
)
async def cancel_section_usta(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    await state.clear()
    await message.answer("Bekor qilindi.")


@router.message(Command("sections"), F.from_user.id == ADMIN_ID)
async def cmd_sections(message: Message) -> None:
    async with get_session_factory()() as session:
        txt = await _sections_root_text(session)
    await message.answer(
        txt,
        reply_markup=_sections_root_kb(),
        parse_mode="HTML",
    )
