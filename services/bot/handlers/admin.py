"""Admin /admin va callbacklar."""

from html import escape

from aiogram import F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from packages.db.repositories import orders as orders_repo
from packages.db.repositories import section_ustas as section_ustas_repo
from packages.db.repositories import users as users_repo
from packages.db.session import get_session_factory
from services.bot.callback_data import AdminCallback, OrderCallback
from services.bot.formatters import format_order_detail
from services.bot.keyboards import (
    BTN_ADMIN_ACCEPTED,
    BTN_ADMIN_DONE,
    BTN_ADMIN_NEW,
    BTN_ADMIN_ORDERS,
    BTN_ADMIN_PENDING_USTAS,
    BTN_ADMIN_SECTIONS,
    BTN_ADMIN_STATS,
    BTN_ADMIN_USTAS,
    admin_main_keyboard,
)
from services.bot.callback_data import SectionCallback, UstaApprovalCallback
from services.bot.i18n import t, LANG_UZ, LANG_RU
from services.bot.router import router
from shared.config import get_settings

settings = get_settings()
ADMIN_ID = settings.admin_chat_id


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not message.from_user or message.from_user.id != ADMIN_ID:
        await message.answer("Bu buyruq faqat admin uchun.")
        return
    async with get_session_factory()() as session:
        today = await orders_repo.count_orders_today(session)
        total = await orders_repo.count_all_orders(session)
    await message.answer(
        "👤 <b>Admin panel</b>\n\n"
        f"📊 Bugun (UTC+5, O'zbekiston): <b>{today}</b> ta buyurtma\n"
        f"📁 Jami saqlangan: <b>{total}</b> ta\n\n"
        "Pastdagi tugmalardan foydalaning.",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(AdminCallback.filter(F.action == "menu"), F.from_user.id == ADMIN_ID)
async def cb_admin_menu(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        today = await orders_repo.count_orders_today(session)
        total = await orders_repo.count_all_orders(session)
    await call.message.edit_text(
        "👤 <b>Admin panel</b>\n\n"
        f"📊 Bugun (UTC+5, O'zbekiston): <b>{today}</b> ta buyurtma\n"
        f"📁 Jami saqlangan: <b>{total}</b> ta\n\n"
        "Pastdagi tugmalardan foydalaning.",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(AdminCallback.filter(F.action == "stats"), F.from_user.id == ADMIN_ID)
async def cb_admin_stats(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        today = await orders_repo.count_orders_today(session)
        total = await orders_repo.count_all_orders(session)
    await call.message.edit_text(
        "📊 <b>Statistika</b>\n\n"
        f"Bugun (UTC+5): {today} ta\n"
        f"Jami: {total} ta\n\n"
        "Batafsil filtrlash keyingi versiyada.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ Admin bosh sahifa",
                        callback_data=AdminCallback(action="menu").pack(),
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )
    await call.answer()


def _orders_tab_keyboard(active: str = "") -> InlineKeyboardMarkup:
    """3 tabli buyurtmalar menyusi."""
    def _btn(text: str, action: str) -> InlineKeyboardButton:
        label = f"[ {text} ]" if action == active else text
        return InlineKeyboardButton(
            text=label,
            callback_data=AdminCallback(action=action).pack(),
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn("🆕 Yangi", "list_new"),
                _btn("✅ Qabul qilingan", "list_accepted"),
                _btn("🏁 Tugatilgan", "list_done"),
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Admin bosh sahifa",
                    callback_data=AdminCallback(action="menu").pack(),
                )
            ],
        ]
    )


def _build_orders_list_text(rows: list, tab_label: str) -> tuple[str, list]:
    """Ro'yxat matni va tugmalar."""
    if not rows:
        return f"📋 <b>{tab_label}</b>\n\nHozircha buyurtmalar yo'q.", []
    lines = [f"📋 <b>{tab_label}</b> (batafsil uchun tugmani bosing):\n"]
    buttons: list[list[InlineKeyboardButton]] = []
    for r in rows:
        svc = (r["service"] or "")[:30]
        label = f"#{r['id']} • {svc}"
        if r.get("accepted_usta_name"):
            label += f" • {r['accepted_usta_name']}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=OrderCallback(action="view", order_id=r["id"]).pack(),
                )
            ]
        )
    return "\n".join(lines), buttons


@router.callback_query(AdminCallback.filter(F.action == "list"), F.from_user.id == ADMIN_ID)
async def cb_admin_list(call: CallbackQuery) -> None:
    """Buyurtmalar tab menyusini ko'rsatish."""
    await call.message.edit_text(
        "📋 <b>Buyurtmalar</b>\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=_orders_tab_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(AdminCallback.filter(F.action == "list_new"), F.from_user.id == ADMIN_ID)
async def cb_admin_list_new(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        rows = await orders_repo.list_orders_by_status(session, "new", 20)
    txt, buttons = _build_orders_list_text(rows, "🆕 Yangi buyurtmalar")
    buttons.append(
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=AdminCallback(action="list").pack())]
    )
    await call.message.edit_text(
        txt,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(AdminCallback.filter(F.action == "list_accepted"), F.from_user.id == ADMIN_ID)
async def cb_admin_list_accepted(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        rows = await orders_repo.list_orders_by_status(session, "accepted", 20)
    txt, buttons = _build_orders_list_text(rows, "✅ Qabul qilingan buyurtmalar")
    buttons.append(
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=AdminCallback(action="list").pack())]
    )
    await call.message.edit_text(
        txt,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(AdminCallback.filter(F.action == "list_done"), F.from_user.id == ADMIN_ID)
async def cb_admin_list_done(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        rows = await orders_repo.list_orders_by_status(session, "done", 20)
    txt, buttons = _build_orders_list_text(rows, "🏁 Tugatilgan buyurtmalar")
    buttons.append(
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=AdminCallback(action="list").pack())]
    )
    await call.message.edit_text(
        txt,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(OrderCallback.filter(F.action == "view"), F.from_user.id == ADMIN_ID)
async def cb_order_view(call: CallbackQuery, callback_data: OrderCallback) -> None:
    async with get_session_factory()() as session:
        row = await orders_repo.get_order(session, callback_data.order_id)
    if not row:
        await call.answer("Buyurtma topilmadi", show_alert=True)
        return

    kb_rows: list[list[InlineKeyboardButton]] = []

    # "Ustaga berish" — faqat yangi va section_id bo'lgan buyurtmalarda
    if row["status"] == "new" and row.get("section_id"):
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="👷 Ustaga berish",
                    callback_data=OrderCallback(
                        action="assign_pick", order_id=row["id"]
                    ).pack(),
                )
            ]
        )

    if row["status"] in ("new", "accepted"):
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Yakunlandi",
                    callback_data=OrderCallback(
                        action="done", order_id=row["id"]
                    ).pack(),
                )
            ]
        )
    kb_rows.append(
        [
            InlineKeyboardButton(
                text="◀️ Ro'yxat",
                callback_data=AdminCallback(action="list").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Bosh sahifa",
                callback_data=AdminCallback(action="menu").pack(),
            ),
        ]
    )

    await call.message.edit_text(
        format_order_detail(row),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(OrderCallback.filter(F.action == "done"), F.from_user.id == ADMIN_ID)
async def cb_order_done(call: CallbackQuery, callback_data: OrderCallback) -> None:
    async with get_session_factory()() as session:
        ok = await orders_repo.set_order_status(
            session, callback_data.order_id, "done"
        )
        if not ok:
            await call.answer("Yangilanmadi", show_alert=True)
            return
        row = await orders_repo.get_order(session, callback_data.order_id)
    if row:
        await call.message.edit_text(
            format_order_detail(row) + "\n\n✅ <b>Yakunlandi</b>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="◀️ Ro'yxat",
                            callback_data=AdminCallback(action="list").pack(),
                        )
                    ]
                ]
            ),
            parse_mode="HTML",
        )
    await call.answer("Saqlendi")


@router.callback_query(OrderCallback.filter(F.action == "assign_pick"), F.from_user.id == ADMIN_ID)
async def cb_order_assign_pick(call: CallbackQuery, callback_data: OrderCallback) -> None:
    """Admin buyurtma uchun usta tanlash ro'yxatini ko'rsatadi."""
    async with get_session_factory()() as session:
        row = await orders_repo.get_order(session, callback_data.order_id)
        if not row or row["status"] != "new" or not row.get("section_id"):
            await call.answer("Buyurtma topilmadi yoki allaqachon qabul qilingan", show_alert=True)
            return
        ustas = await section_ustas_repo.list_claimed_for_section(session, row["section_id"])

    if not ustas:
        await call.answer("Bu bo'limda faol usta yo'q (hech kim /start usta bosmagan)", show_alert=True)
        return

    kb: list[list[InlineKeyboardButton]] = []
    for u in ustas:
        stars = ""
        if u["avg_rating"] is not None:
            stars = f" ⭐{u['avg_rating']:.1f}"
        label = f"👷 {u['display_name']}{stars} — {u['phone_normalized'] or ''}".strip(" —")
        kb.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=OrderCallback(
                        action="assign_usta",
                        order_id=callback_data.order_id,
                        suid=u["id"],
                    ).pack(),
                )
            ]
        )
    kb.append(
        [
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data=OrderCallback(action="view", order_id=callback_data.order_id).pack(),
            )
        ]
    )
    await call.message.edit_text(
        f"👷 <b>Buyurtma #{callback_data.order_id} uchun usta tanlang:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(OrderCallback.filter(F.action == "assign_usta"), F.from_user.id == ADMIN_ID)
async def cb_order_assign_usta(call: CallbackQuery, callback_data: OrderCallback) -> None:
    """Admin tanlagan ustaga buyurtmani biriktiradi."""
    import logging
    log = logging.getLogger(__name__)

    async with get_session_factory()() as session:
        result, name, phone = await orders_repo.admin_assign_order(
            session, order_id=callback_data.order_id, section_usta_id=callback_data.suid
        )

    if result == "no_usta":
        await call.answer("Usta topilmadi yoki hali Telegram bilan ulamagan", show_alert=True)
        return
    if result == "race":
        await call.answer("Buyurtma allaqachon qabul qilingan yoki topilmadi", show_alert=True)
        return

    # Ustaga xabar yuborish
    async with get_session_factory()() as session:
        row = await orders_repo.get_order(session, callback_data.order_id)
        su_row = await section_ustas_repo.get_by_id(session, callback_data.suid)

    if row and su_row and su_row.telegram_id:
        from services.bot.handlers.orders import _client_finish_kb

        try:
            extra_addr = ""
            if row.get("service_address_note"):
                extra_addr = f"\n📌 Ish joyi: {row['service_address_note']}"
            await call.bot.send_message(
                chat_id=int(su_row.telegram_id),
                text=(
                    f"📋 Administrator yangi buyurtmani sizga yubordi:\n\n"
                    f"🆔 Buyurtma #{row['id']}\n"
                    f"🔧 Xizmat: {row['service']}\n"
                    f"📝 Muammo: {row['problem']}"
                    f"{extra_addr}\n"
                    f"👤 Mijoz: {row.get('client_name') or '—'}\n"
                    f"📞 Tel: {row.get('phone') or '—'}\n"
                    f"💬 Chat: tg://user?id={row['client_tg_id']}"
                ),
            )
        except Exception as exc:
            log.error("assign_usta: ustaga xabar yuborishda xato: %s", exc)

        client_id = int(row["client_tg_id"])
        async with get_session_factory()() as session:
            cloc = await users_repo.get_locale(session, client_id)
        finish_hint = escape(t(cloc, "order.client_finish_hint"))
        safe_assign_name = escape(name or "")
        safe_assign_phone = escape(phone or "")
        try:
            await call.bot.send_message(
                chat_id=client_id,
                text=t(
                    cloc,
                    "order.admin_assigned_client",
                    oid=str(row["id"]),
                    name=safe_assign_name,
                    phone=safe_assign_phone,
                    finish_hint=finish_hint,
                ),
                parse_mode="HTML",
                reply_markup=_client_finish_kb(row["id"], cloc),
            )
        except Exception as exc:
            log.error("assign_usta: mijozga tayinlash xabari: %s", exc)

    await call.message.edit_text(
        f"✅ Buyurtma #{callback_data.order_id} — <b>{name}</b> ustaga tayinlandi.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ Ro'yxat",
                        callback_data=AdminCallback(action="list").pack(),
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )
    await call.answer("Tayinlandi ✅")


# ---- ADMIN REPLY KEYBOARD HANDLERLARI ----

@router.message(F.text == BTN_ADMIN_ORDERS, F.from_user.id == ADMIN_ID)
async def msg_admin_orders(message: Message) -> None:
    await message.answer(
        "📋 <b>Buyurtmalar</b>\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=_orders_tab_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == BTN_ADMIN_NEW, F.from_user.id == ADMIN_ID)
async def msg_admin_new_orders(message: Message) -> None:
    async with get_session_factory()() as session:
        rows = await orders_repo.list_orders_by_status(session, "new", 20)
    txt, buttons = _build_orders_list_text(rows, "🆕 Yangi buyurtmalar")
    buttons.append(
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=AdminCallback(action="list").pack())]
    )
    await message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@router.message(F.text == BTN_ADMIN_ACCEPTED, F.from_user.id == ADMIN_ID)
async def msg_admin_accepted_orders(message: Message) -> None:
    async with get_session_factory()() as session:
        rows = await orders_repo.list_orders_by_status(session, "accepted", 20)
    txt, buttons = _build_orders_list_text(rows, "✅ Qabul qilingan buyurtmalar")
    buttons.append(
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=AdminCallback(action="list").pack())]
    )
    await message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@router.message(F.text == BTN_ADMIN_DONE, F.from_user.id == ADMIN_ID)
async def msg_admin_done_orders(message: Message) -> None:
    async with get_session_factory()() as session:
        rows = await orders_repo.list_orders_by_status(session, "done", 20)
    txt, buttons = _build_orders_list_text(rows, "🏁 Tugatilgan buyurtmalar")
    buttons.append(
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=AdminCallback(action="list").pack())]
    )
    await message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@router.message(F.text == BTN_ADMIN_STATS, F.from_user.id == ADMIN_ID)
async def msg_admin_stats(message: Message) -> None:
    async with get_session_factory()() as session:
        today = await orders_repo.count_orders_today(session)
        total = await orders_repo.count_all_orders(session)
    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"Bugun (UTC+5): <b>{today}</b> ta\n"
        f"Jami: <b>{total}</b> ta",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ Admin bosh sahifa",
                        callback_data=AdminCallback(action="menu").pack(),
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )


@router.message(F.text == BTN_ADMIN_SECTIONS, F.from_user.id == ADMIN_ID)
async def msg_admin_sections(message: Message) -> None:
    from services.bot.handlers.sections_admin import (
        _sections_root_kb,
        _sections_root_text,
    )
    async with get_session_factory()() as session:
        txt = await _sections_root_text(session)
    await message.answer(
        txt,
        reply_markup=_sections_root_kb(),
        parse_mode="HTML",
    )


@router.message(F.text == BTN_ADMIN_USTAS, F.from_user.id == ADMIN_ID)
async def msg_admin_ustas(message: Message) -> None:
    from services.bot.handlers.sections_admin import (
        _sections_root_kb,
        _section_row_kb,
    )
    from packages.db.repositories import sections as sections_repo
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from html import escape

    async with get_session_factory()() as session:
        rows = await sections_repo.list_all(session)

    if not rows:
        await message.answer("Bo'limlar yo'q. Avval bo'lim qo'shing.")
        return

    lines = ["<b>Bo'limni tanlang — usta qo'shish uchun 👤 Usta tugmasini bosing</b>\n"]
    kb: list[list[InlineKeyboardButton]] = []
    for r in rows:
        st = "✅" if r["is_active"] else "⏸"
        lines.append(f"{st} #{r['id']} — {escape(r['title'])}")
        kb.append(_section_row_kb(r["id"]))
    kb.append(
        [
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data=SectionCallback(action="menu", sid=0).pack(),
            )
        ]
    )
    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML",
    )


@router.message(F.text == BTN_ADMIN_PENDING_USTAS, F.from_user.id == ADMIN_ID)
async def msg_admin_pending_ustas(message: Message) -> None:
    """O'zi ro'yxatdan o'tgan, admin tasdiqlashni kutayotgan ustalar."""
    async with get_session_factory()() as session:
        pending = await section_ustas_repo.list_pending_approval(session)

    if not pending:
        await message.answer("⏳ Hozircha kutayotgan usta yo'q.")
        return

    lines = ["<b>⏳ Admin tasdiqlashni kutayotgan ustalar:</b>\n"]
    kb: list[list[InlineKeyboardButton]] = []

    for usta in pending:
        section_id = usta.get("section_id", 0)
        usta_id = usta.get("id", 0)
        display_name = escape(usta.get("display_name", "?"))
        phone = escape(usta.get("phone", "—"))

        lines.append(f"👤 {display_name} ({phone})")

        kb.append(
            [
                InlineKeyboardButton(
                    text=f"✅ {display_name}",
                    callback_data=UstaApprovalCallback(
                        action="approve", usta_id=usta_id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=UstaApprovalCallback(
                        action="reject", usta_id=usta_id
                    ).pack(),
                ),
            ]
        )

    kb.append(
        [
            InlineKeyboardButton(
                text="◀️ Admin bosh sahifa",
                callback_data=AdminCallback(action="menu").pack(),
            )
        ]
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML",
    )


# ---- USTA SELF-REGISTRATION ----

async def notify_admin_pending_usta(usta_row) -> None:
    """Yangi usta ariza yuborilganda adminga darhol xabar beramiz (retry bilan)."""
    import logging
    log = logging.getLogger(__name__)

    async with get_session_factory()() as session:
        section_row = await session.get(
            __import__('packages.db.models', fromlist=['Section']).Section,
            usta_row.section_id
        )

    section_title = section_row.title if section_row else "—"
    name_esc = escape(f"{usta_row.first_name} {usta_row.last_name or ''}".strip())
    phone_esc = escape(usta_row.phone or "—")

    text = (
        f"⏳ <b>YANGI USTA ARIZA</b>\n\n"
        f"👤 {name_esc}\n"
        f"📞 {phone_esc}\n"
        f"🔧 {escape(section_title)}\n\n"
        f"<b>Darhol:</b> Pastdagi tugmalardan foydalaning"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ TASDIQLASH",
                    callback_data=UstaApprovalCallback(
                        action="approve", usta_id=usta_row.id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ RAD ETISH",
                    callback_data=UstaApprovalCallback(
                        action="reject", usta_id=usta_row.id
                    ).pack(),
                ),
            ]
        ]
    )

    # Retry logic: 3 marta urinish
    max_retries = 3
    for attempt in range(max_retries):
        try:
            bot = __import__('aiogram').Bot(token=settings.bot_token)
            msg = await bot.send_message(
                chat_id=ADMIN_ID,
                text=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
            log.info(
                "admin_notified: usta_id=%s name=%s attempt=%d",
                usta_row.id,
                name_esc,
                attempt + 1,
            )
            return  # Success
        except Exception as exc:
            if attempt < max_retries - 1:
                # Retry after a short delay
                import asyncio
                await asyncio.sleep(1)
                log.warning(
                    "notify_retry: usta_id=%s attempt=%d error=%s",
                    usta_row.id,
                    attempt + 1,
                    str(exc),
                )
            else:
                # Final attempt failed
                log.error(
                    "notify_failed: usta_id=%s name=%s error=%s",
                    usta_row.id,
                    name_esc,
                    str(exc),
                )


@router.callback_query(UstaApprovalCallback.filter(F.action == "approve"), F.from_user.id == ADMIN_ID)
async def cb_usta_approve(call: CallbackQuery, callback_data: UstaApprovalCallback) -> None:
    """Admin usta arizasini tasdiqladi."""
    async with get_session_factory()() as session:
        ok = await section_ustas_repo.approve_usta(session, callback_data.usta_id)
        if ok:
            usta_row = await section_ustas_repo.get_by_id(session, callback_data.usta_id)
        else:
            usta_row = None

    if not ok:
        await call.answer("Arizani topib bo'lmasdik yoki allaqachon qayta işlangan", show_alert=True)
        return

    # Ustaga xabar yuborish
    if usta_row and usta_row.telegram_id:
        async with get_session_factory()() as session:
            section_row = await session.get(
                __import__('packages.db.models', fromlist=['Section']).Section,
                usta_row.section_id
            )
            # Get usta's language preference
            user_row = await users_repo.get_by_id(session, usta_row.telegram_id)
            usta_lang = (user_row.locale if user_row else None) or LANG_UZ
        section_title = section_row.title if section_row else "—"
        name_esc = escape(f"{usta_row.first_name} {usta_row.last_name or ''}".strip())

        try:
            await call.bot.send_message(
                chat_id=usta_row.telegram_id,
                text=t(usta_lang, "usta.approved", section=escape(section_title)),
                parse_mode="HTML",
            )
        except Exception as exc:
            import logging
            log = logging.getLogger(__name__)
            log.error("cb_usta_approve: ustaga xabar yuborishda xato: %s", exc)

    await call.message.edit_text(
        f"✅ <b>Usta tasdiqlandi:</b> {name_esc}",
        parse_mode="HTML",
    )
    await call.answer("Tasdiqlandi ✅")


@router.callback_query(UstaApprovalCallback.filter(F.action == "reject"), F.from_user.id == ADMIN_ID)
async def cb_usta_reject(call: CallbackQuery, callback_data: UstaApprovalCallback) -> None:
    """Admin usta arizasini rad etdi."""
    import logging
    log = logging.getLogger(__name__)

    async with get_session_factory()() as session:
        usta_row = await section_ustas_repo.get_by_id(session, callback_data.usta_id)
        ok = await section_ustas_repo.reject_usta(session, callback_data.usta_id)

    if not ok:
        await call.answer("Arizani topib bo'lmasdik", show_alert=True)
        return

    # Ustaga xabar yuborish
    if usta_row and usta_row.telegram_id:
        async with get_session_factory()() as session:
            user_row = await users_repo.get_by_id(session, usta_row.telegram_id)
            usta_lang = (user_row.locale if user_row else None) or LANG_UZ
        try:
            await call.bot.send_message(
                chat_id=usta_row.telegram_id,
                text=t(usta_lang, "usta.rejected"),
                parse_mode="HTML",
            )
        except Exception as exc:
            log.error("cb_usta_reject: ustaga xabar yuborishda xato: %s", exc)

    name_esc = escape(f"{usta_row.first_name if usta_row else '?'}")
    await call.message.edit_text(
        f"❌ <b>Usta rad etildi:</b> {name_esc}",
        parse_mode="HTML",
    )
    await call.answer("Rad etildi ❌")
