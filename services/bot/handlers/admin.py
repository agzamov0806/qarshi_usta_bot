"""Admin /admin va callbacklar."""

from aiogram import F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from packages.db.repositories import orders as orders_repo
from packages.db.session import get_session_factory
from services.bot.callback_data import AdminCallback, OrderCallback
from services.bot.formatters import format_order_detail
from services.bot.keyboards import admin_main_keyboard
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


@router.callback_query(AdminCallback.filter(F.action == "list"), F.from_user.id == ADMIN_ID)
async def cb_admin_list(call: CallbackQuery) -> None:
    async with get_session_factory()() as session:
        rows = await orders_repo.list_recent_orders(session, 10)
    if not rows:
        await call.message.edit_text(
            "📋 Hozircha buyurtmalar yo'q.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="◀️ Orqaga",
                            callback_data=AdminCallback(action="menu").pack(),
                        )
                    ]
                ]
            ),
        )
        await call.answer()
        return

    lines = ["📋 <b>Oxirgi buyurtmalar</b> (batafsil uchun tugmani bosing):\n"]
    buttons: list[list[InlineKeyboardButton]] = []
    for r in rows:
        label = f"#{r['id']} • {r['service']} • {r['status']}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=OrderCallback(
                        action="view", order_id=r["id"]
                    ).pack(),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="◀️ Admin bosh sahifa",
                callback_data=AdminCallback(action="menu").pack(),
            )
        ]
    )

    await call.message.edit_text(
        "\n".join(lines),
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
    if row["status"] == "new":
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
