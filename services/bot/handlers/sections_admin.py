"""Admin: bo'limlar CRUD (Telegram)."""

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from packages.db.repositories import sections as sections_repo
from packages.db.repositories.sections import (
    KIND_ADMIN_CONTACT,
    KIND_LABELS,
    KIND_STANDARD,
    KIND_SUGGESTION,
)
from packages.db.session import get_session_factory
from services.bot.callback_data import AdminCallback, SectionCallback, SectionKindCallback
from services.bot.router import router
from services.bot.states import SectionAdminStates
from shared.config import get_settings
from sqlalchemy.exc import IntegrityError

settings = get_settings()
ADMIN_ID = settings.admin_chat_id


def _is_admin(uid: int | None) -> bool:
    return uid is not None and uid == ADMIN_ID


async def _sections_root_text(session) -> str:
    rows = await sections_repo.list_all(session)
    lines = ["📂 <b>Bo'limlar boshqaruvi</b>\n"]
    if not rows:
        lines.append("Hozircha bo'lim yo'q. «➕ Qo'shish»dan boshlang.")
    else:
        for r in rows:
            st = "✅" if r["is_active"] else "⏸"
            lines.append(
                f"{r['id']}. {st} <b>{r['title']}</b>\n   "
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
        lines.append(f"{st} #{r['id']} — {r['title']}")
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
            lines.append(f"{st} #{r['id']} — {r['title']}")
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
        lines.append(f"{st} #{r['id']} — {r['title']}")
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


@router.message(Command("sections"), F.from_user.id == ADMIN_ID)
async def cmd_sections(message: Message) -> None:
    async with get_session_factory()() as session:
        txt = await _sections_root_text(session)
    await message.answer(
        txt,
        reply_markup=_sections_root_kb(),
        parse_mode="HTML",
    )
