"""Buyurtma oqimi."""

import asyncio
import logging

from aiogram import Bot, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Location,
    Message,
    ReplyKeyboardRemove,
)

from packages.db.repositories import orders as orders_repo
from packages.db.repositories import sections as sections_repo
from packages.db.repositories import users as users_repo
from packages.db.repositories.sections import (
    KIND_ADMIN_CONTACT,
    KIND_SUGGESTION,
)
from packages.db.session import get_session_factory
from services.bot.callback_data import OrderCallback
from services.bot.filters import ActiveSectionTitleFilter
from services.bot.formatters import (
    build_admin_notify_user_block,
    display_name_from_user,
)
from services.bot.i18n import (
    back_detail_labels,
    back_sections_labels,
    t,
)
from services.bot.keyboards import (
    build_elektrik_detail_keyboard,
    build_elektrik_sub_keyboard,
    build_konditsioner_detail_keyboard,
    build_konditsioner_sub_keyboard,
    build_mebel_detail_keyboard,
    build_mebel_sub_keyboard,
    build_payvandlash_detail_keyboard,
    build_payvandlash_sub_keyboard,
    build_santexnika_detail_keyboard,
    build_santexnika_sub_keyboard,
    build_services_keyboard,
    build_tv_maishiy_detail_keyboard,
    build_tv_maishiy_sub_keyboard,
    is_elektrik_section_title,
    is_konditsioner_section_title,
    is_mebel_section_title,
    is_payvandlash_section_title,
    is_santexnika_section_title,
    is_tv_maishiy_section_title,
    location_request_keyboard,
    nested_detail_map_for_flow,
    nested_subs_for_flow,
)
from services.bot.router import router
from services.bot.states import OrderStates
from shared.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()
ADMIN_ID = settings.admin_chat_id


async def _send_admin_order_notice(
    bot: Bot,
    *,
    admin_chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    order_id: int,
) -> None:
    """Mijoz javobidan keyin fon rejimida — Telegram API bloklamaslik uchun."""
    try:
        await bot.send_message(
            admin_chat_id,
            text,
            reply_markup=reply_markup,
        )
    except Exception:
        log.exception("Admin ga buyurtma #%s xabari yuborilmadi (fon)", order_id)

NESTED_FLOW_SANTEXNIKA = "santexnika"
NESTED_FLOW_PAYVANDLASH = "payvandlash"
NESTED_FLOW_ELEKTRIK = "elektrik"
NESTED_FLOW_MEBEL = "mebel"
NESTED_FLOW_TV_MAISHIY = "tv_maishiy"
NESTED_FLOW_KONDITSIONER = "konditsioner"

_FLOW_L2_I18N: dict[str, str] = {
    NESTED_FLOW_SANTEXNIKA: "flow.santexnika",
    NESTED_FLOW_PAYVANDLASH: "flow.payvandlash",
    NESTED_FLOW_ELEKTRIK: "flow.elektr",
    NESTED_FLOW_MEBEL: "flow.mebel",
    NESTED_FLOW_TV_MAISHIY: "flow.tv",
    NESTED_FLOW_KONDITSIONER: "flow.kond",
}

_BACK_SECTION_LABELS = back_sections_labels()
_BACK_DETAIL_LABELS = back_detail_labels()


async def _locale_for_user(uid: int) -> str:
    async with get_session_factory()() as session:
        return await users_repo.get_locale(session, uid)


async def _continue_order_after_selection(
    message: Message,
    state: FSMContext,
    bot: Bot,
    *,
    problem_text: str,
    loc: str,
) -> None:
    """Tanlov tugagach muammoni avtomatik to'ldirish; qo'shimcha matn so'ralmaydi."""
    await state.update_data(problem=problem_text.strip())
    await state.set_state(OrderStates.waiting_location_choice)
    await message.answer(
        t(loc, "order.location_prompt"),
        reply_markup=location_request_keyboard(loc),
    )


def _nested_build_sub_kb(flow: str, locale: str):
    if flow == NESTED_FLOW_SANTEXNIKA:
        return build_santexnika_sub_keyboard(locale)
    if flow == NESTED_FLOW_PAYVANDLASH:
        return build_payvandlash_sub_keyboard(locale)
    if flow == NESTED_FLOW_ELEKTRIK:
        return build_elektrik_sub_keyboard(locale)
    if flow == NESTED_FLOW_MEBEL:
        return build_mebel_sub_keyboard(locale)
    if flow == NESTED_FLOW_TV_MAISHIY:
        return build_tv_maishiy_sub_keyboard(locale)
    if flow == NESTED_FLOW_KONDITSIONER:
        return build_konditsioner_sub_keyboard(locale)
    return build_santexnika_sub_keyboard(locale)


def _nested_build_detail_kb(flow: str, parent_sub: str, locale: str):
    if flow == NESTED_FLOW_SANTEXNIKA:
        return build_santexnika_detail_keyboard(parent_sub, locale)
    if flow == NESTED_FLOW_PAYVANDLASH:
        return build_payvandlash_detail_keyboard(parent_sub, locale)
    if flow == NESTED_FLOW_ELEKTRIK:
        return build_elektrik_detail_keyboard(parent_sub, locale)
    if flow == NESTED_FLOW_MEBEL:
        return build_mebel_detail_keyboard(parent_sub, locale)
    if flow == NESTED_FLOW_TV_MAISHIY:
        return build_tv_maishiy_detail_keyboard(parent_sub, locale)
    if flow == NESTED_FLOW_KONDITSIONER:
        return build_konditsioner_detail_keyboard(parent_sub, locale)
    return build_santexnika_detail_keyboard(parent_sub, locale)


def _nested_header_l2_html(flow: str, locale: str) -> str:
    key = _FLOW_L2_I18N.get(flow)
    if key:
        return t(locale, key)
    return t(locale, "flow.santexnika")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await state.clear()
    await message.answer(
        t(loc, "order.cancel"),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(
    StateFilter(None),
    ActiveSectionTitleFilter(),
)
async def service_chosen(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    async with get_session_factory()() as session:
        if uid != ADMIN_ID and not await users_repo.is_registered(session, uid):
            await message.answer(t(loc, "order.need_register"))
            return
        sec = await sections_repo.get_active_by_title(session, message.text.strip())
        if not sec:
            await message.answer(t(loc, "order.section_missing"))
            return
        kind = sec.kind
        title = sec.title

    if is_santexnika_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            nested_flow=NESTED_FLOW_SANTEXNIKA,
        )
        await state.set_state(OrderStates.waiting_sub_service)
        await message.answer(
            _nested_header_l2_html(NESTED_FLOW_SANTEXNIKA, loc),
            parse_mode="HTML",
            reply_markup=_nested_build_sub_kb(NESTED_FLOW_SANTEXNIKA, loc),
        )
        return

    if is_payvandlash_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            nested_flow=NESTED_FLOW_PAYVANDLASH,
        )
        await state.set_state(OrderStates.waiting_sub_service)
        await message.answer(
            _nested_header_l2_html(NESTED_FLOW_PAYVANDLASH, loc),
            parse_mode="HTML",
            reply_markup=_nested_build_sub_kb(NESTED_FLOW_PAYVANDLASH, loc),
        )
        return

    if is_elektrik_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            nested_flow=NESTED_FLOW_ELEKTRIK,
        )
        await state.set_state(OrderStates.waiting_sub_service)
        await message.answer(
            _nested_header_l2_html(NESTED_FLOW_ELEKTRIK, loc),
            parse_mode="HTML",
            reply_markup=_nested_build_sub_kb(NESTED_FLOW_ELEKTRIK, loc),
        )
        return

    if is_mebel_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            nested_flow=NESTED_FLOW_MEBEL,
        )
        await state.set_state(OrderStates.waiting_sub_service)
        await message.answer(
            _nested_header_l2_html(NESTED_FLOW_MEBEL, loc),
            parse_mode="HTML",
            reply_markup=_nested_build_sub_kb(NESTED_FLOW_MEBEL, loc),
        )
        return

    if is_tv_maishiy_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            nested_flow=NESTED_FLOW_TV_MAISHIY,
        )
        await state.set_state(OrderStates.waiting_sub_service)
        await message.answer(
            _nested_header_l2_html(NESTED_FLOW_TV_MAISHIY, loc),
            parse_mode="HTML",
            reply_markup=_nested_build_sub_kb(NESTED_FLOW_TV_MAISHIY, loc),
        )
        return

    if is_konditsioner_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            nested_flow=NESTED_FLOW_KONDITSIONER,
        )
        await state.set_state(OrderStates.waiting_sub_service)
        await message.answer(
            _nested_header_l2_html(NESTED_FLOW_KONDITSIONER, loc),
            parse_mode="HTML",
            reply_markup=_nested_build_sub_kb(NESTED_FLOW_KONDITSIONER, loc),
        )
        return

    await state.update_data(service=title, section_kind=kind)
    await _continue_order_after_selection(
        message,
        state,
        message.bot,
        problem_text=title,
        loc=loc,
    )


@router.message(
    StateFilter(OrderStates.waiting_sub_service),
    F.text.in_(_BACK_SECTION_LABELS),
)
async def nested_sub_back_to_sections(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await state.clear()
    async with get_session_factory()() as session:
        kb = await build_services_keyboard(session, loc)
    await message.answer(
        t(loc, "order.back_sections"),
        reply_markup=kb,
    )


@router.message(StateFilter(OrderStates.waiting_sub_service), F.text)
async def nested_sub_l2_chosen(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    text = (message.text or "").strip()
    data = await state.get_data()
    flow = data.get("nested_flow")
    subs = nested_subs_for_flow(flow, loc) if flow else ()
    if not subs:
        await message.answer(t(loc, "order.session_nested_bad"))
        return
    if text not in subs:
        await message.answer(t(loc, "order.pick_sub"))
        return

    details_map = nested_detail_map_for_flow(flow, loc)
    details = details_map.get(text)
    if details:
        await state.update_data(nested_l2=text)
        await state.set_state(OrderStates.waiting_sub_detail)
        await message.answer(
            t(loc, "nested.l3_prompt", title=text),
            parse_mode="HTML",
            reply_markup=_nested_build_detail_kb(flow, text, loc),
        )
        return

    base = data.get("service") or "?"
    await state.update_data(service=f"{base} — {text}")
    await _continue_order_after_selection(
        message,
        state,
        message.bot,
        problem_text=text,
        loc=loc,
    )


@router.message(
    StateFilter(OrderStates.waiting_sub_detail),
    F.text.in_(_BACK_DETAIL_LABELS),
)
async def nested_detail_back_to_l2(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    data = await state.get_data()
    flow = data.get("nested_flow")
    await state.update_data(nested_l2=None)
    await state.set_state(OrderStates.waiting_sub_service)
    await message.answer(
        _nested_header_l2_html(flow or "", loc),
        parse_mode="HTML",
        reply_markup=_nested_build_sub_kb(flow or "", loc),
    )


@router.message(StateFilter(OrderStates.waiting_sub_detail), F.text)
async def nested_sub_l3_chosen(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    text = (message.text or "").strip()
    data = await state.get_data()
    flow = data.get("nested_flow")
    details_map = nested_detail_map_for_flow(flow, loc) if flow else {}
    l2 = data.get("nested_l2")
    if not details_map or not l2 or l2 not in details_map:
        await state.clear()
        await message.answer(
            t(loc, "order.session_nested_bad"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    valid = details_map[l2]
    if text not in valid:
        await message.answer(t(loc, "order.pick_detail"))
        return

    base = data.get("service") or "?"
    await state.update_data(
        service=f"{base} — {l2} — {text}",
        nested_l2=None,
    )
    await _continue_order_after_selection(
        message,
        state,
        message.bot,
        problem_text=text,
        loc=loc,
    )


@router.message(StateFilter(OrderStates.waiting_sub_detail))
async def nested_sub_detail_bad(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await message.answer(t(loc, "order.detail_non_text"))


@router.message(StateFilter(OrderStates.waiting_sub_service))
async def nested_sub_l2_bad(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await message.answer(t(loc, "order.sub_non_text"))


@router.message(StateFilter(OrderStates.waiting_problem), F.text)
async def problem_received(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await state.update_data(problem=message.text.strip())
    await state.set_state(OrderStates.waiting_location_choice)
    await message.answer(
        t(loc, "order.location_prompt"),
        reply_markup=location_request_keyboard(loc),
    )


@router.message(StateFilter(OrderStates.waiting_problem))
async def problem_not_text(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await message.answer(t(loc, "order.problem_not_text"))


@router.message(StateFilter(OrderStates.waiting_location_choice), F.location)
async def location_received(message: Message, state: FSMContext, bot: Bot) -> None:
    loc: Location = message.location
    await state.update_data(lat=loc.latitude, lon=loc.longitude)
    await finalize_order(message, state, bot)


@router.message(StateFilter(OrderStates.waiting_location_choice))
async def location_hint(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await message.answer(t(loc, "order.location_hint"))


async def finalize_order(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()

    service = data.get("service", "?")
    section_kind = data.get("section_kind")
    problem = data.get("problem", "?")
    lat = data.get("lat")
    lon = data.get("lon")

    user = message.from_user
    client_tg_id = user.id if user else 0
    loc = await _locale_for_user(client_tg_id)

    async with get_session_factory()() as session:
        reg = await users_repo.get_user(session, client_tg_id)
        if client_tg_id != ADMIN_ID and not reg:
            await message.answer(
                t(loc, "order.session_bad"),
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        profile_full_name: str | None = None
        phone: str | None = None
        if reg:
            profile_full_name = f"{reg.first_name} {reg.last_name}".strip()
            phone = reg.phone
            client_name = profile_full_name
        else:
            if user and user.full_name:
                client_name = user.full_name.strip()
            else:
                client_name = display_name_from_user(user)
        username = user.username if user else None

        order_id = await orders_repo.create_order(
            session,
            client_tg_id=client_tg_id,
            client_name=client_name,
            username=username,
            phone=phone,
            service=service,
            section_kind=section_kind,
            problem=problem,
            lat=float(lat) if lat is not None else None,
            lon=float(lon) if lon is not None else None,
        )
        next_kb = await build_services_keyboard(session, loc)

    user_line = (
        build_admin_notify_user_block(
            user, phone, client_tg_id, profile_full_name=profile_full_name
        )
        if user
        else "Mijoz: noma'lum"
    )

    loc_line = "Lokatsiya: kiritilmagan"
    if lat is not None and lon is not None:
        loc_line = (
            f"Lokatsiya: {float(lat):.6f}, {float(lon):.6f}\n"
            f"https://maps.google.com/?q={lat},{lon}"
        )

    if section_kind == KIND_SUGGESTION:
        header = f"📝 Yangi taklif #{order_id}"
        detail_label = "Taklif"
    elif section_kind == KIND_ADMIN_CONTACT:
        header = f"📩 Adminga murojaat #{order_id}"
        detail_label = "Murojaat"
    else:
        header = f"🆕 Yangi buyurtma #{order_id}"
        detail_label = "Muammo"

    text = (
        f"{header}\n"
        f"{user_line}\n"
        f"Xizmat: {service}\n"
        f"{detail_label}: {problem}\n"
        f"{loc_line}"
    )

    notify_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📋 #{order_id} batafsil (panel)",
                    callback_data=OrderCallback(
                        action="view", order_id=order_id
                    ).pack(),
                )
            ]
        ]
    )

    if section_kind == KIND_SUGGESTION:
        ok_txt = t(loc, "order.ok_suggestion")
    elif section_kind == KIND_ADMIN_CONTACT:
        ok_txt = t(loc, "order.ok_admin")
    else:
        ok_txt = t(loc, "order.ok_order")

    await message.answer(ok_txt, reply_markup=next_kb)

    asyncio.create_task(
        _send_admin_order_notice(
            bot,
            admin_chat_id=ADMIN_ID,
            text=text,
            reply_markup=notify_kb,
            order_id=order_id,
        ),
        name=f"admin_notify_order_{order_id}",
    )
