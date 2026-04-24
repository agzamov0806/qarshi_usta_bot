"""Buyurtma oqimi."""

import asyncio
import logging
from html import escape

from aiogram import Bot, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Location,
    Message,
    ReplyKeyboardRemove,
)

from packages.db.repositories import orders as orders_repo
from packages.db.repositories import section_ustas as section_ustas_repo
from packages.db.repositories import sections as sections_repo
from packages.db.repositories import users as users_repo
from packages.db.repositories.sections import (
    KIND_ADMIN_CONTACT,
    KIND_SUGGESTION,
)
from packages.db.models import SectionUsta
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
    nested_entry_list_labels,
    nested_entry_manual_labels,
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
    build_nested_section_entry_keyboard,
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
from services.bot.states import OrderStates, UstaRejectStates
from shared.config import get_settings
from shared.section_titles import display_title_for_locale

log = logging.getLogger(__name__)
settings = get_settings()
ADMIN_ID = settings.admin_chat_id


def _complete_btn_kb(order_id: int, suid: int) -> InlineKeyboardMarkup:
    """Usta uchun 'Tugatish' tugmali inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏁 Tugatish",
                    callback_data=OrderCallback(
                        action="complete", order_id=order_id, suid=suid
                    ).pack(),
                )
            ]
        ]
    )


async def _send_admin_order_notice(
    bot: Bot,
    *,
    admin_chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
    order_id: int,
    recipient: str = "admin",
) -> None:
    """Mijoz javobidan keyin fon rejimida — Telegram API bloklamaslik uchun."""
    try:
        kw: dict = {"chat_id": admin_chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup is not None:
            kw["reply_markup"] = reply_markup
        await bot.send_message(**kw)
    except TelegramBadRequest as e:
        msg = (e.message or "").lower()
        if "chat not found" in msg or "peer_id_invalid" in msg:
            log.error(
                "Buyurtma #%s: %s chat_id=%s — Telegram xabar yubormadi (%s). "
                "Usta uchun: ID telefon raqami emas, balki @userinfobot dagi raqam bo‘lishi kerak; "
                "usta avval shu botda /start bosgan bo‘lishi shart.",
                order_id,
                recipient,
                admin_chat_id,
                e.message,
            )
        else:
            log.exception(
                "Buyurtma #%s: %s chat_id=%s — TelegramBadRequest",
                order_id,
                recipient,
                admin_chat_id,
            )
    except Exception:
        log.exception(
            "Buyurtma #%s: %s chat_id=%s ga yuborilmadi (fon)",
            order_id,
            recipient,
            admin_chat_id,
        )

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
_NESTED_ENTRY_LIST = nested_entry_list_labels()
_NESTED_ENTRY_MANUAL = nested_entry_manual_labels()

_FLOWS_WITH_NESTED_ENTRY = frozenset(
    {
        NESTED_FLOW_SANTEXNIKA,
        NESTED_FLOW_PAYVANDLASH,
        NESTED_FLOW_ELEKTRIK,
        NESTED_FLOW_MEBEL,
        NESTED_FLOW_TV_MAISHIY,
        NESTED_FLOW_KONDITSIONER,
    }
)


def _nested_entry_prompt_html(loc: str, db_service_title: str) -> str:
    label = escape(display_title_for_locale(db_service_title, loc))
    return t(loc, "order.nested_entry_prompt", title=label)


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
    StateFilter(OrderStates.waiting_nested_section_entry),
    F.text.in_(_BACK_SECTION_LABELS),
)
async def nested_entry_back_sections(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await state.clear()
    async with get_session_factory()() as session:
        kb = await build_services_keyboard(session, loc)
    await message.answer(
        t(loc, "order.back_sections"),
        reply_markup=kb,
    )


@router.message(
    StateFilter(OrderStates.waiting_nested_section_entry),
    F.text.in_(_NESTED_ENTRY_LIST),
)
async def nested_entry_chose_list(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    data = await state.get_data()
    flow = data.get("nested_flow")
    if not flow:
        await message.answer(t(loc, "order.session_nested_bad"))
        return
    await state.set_state(OrderStates.waiting_sub_service)
    await message.answer(
        _nested_header_l2_html(flow, loc),
        parse_mode="HTML",
        reply_markup=_nested_build_sub_kb(flow, loc),
    )


@router.message(
    StateFilter(OrderStates.waiting_nested_section_entry),
    F.text.in_(_NESTED_ENTRY_MANUAL),
)
async def nested_entry_chose_manual(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await state.set_state(OrderStates.waiting_problem)
    await message.answer(
        t(loc, "prompt.problem"),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(StateFilter(OrderStates.waiting_nested_section_entry), F.text)
async def nested_entry_invalid(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale_for_user(uid)
    await message.answer(
        t(loc, "order.nested_entry_pick"),
        reply_markup=build_nested_section_entry_keyboard(loc),
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
        section_db_id = sec.id

    if is_santexnika_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            section_id=section_db_id,
            nested_flow=NESTED_FLOW_SANTEXNIKA,
        )
        await state.set_state(OrderStates.waiting_nested_section_entry)
        await message.answer(
            _nested_entry_prompt_html(loc, title),
            parse_mode="HTML",
            reply_markup=build_nested_section_entry_keyboard(loc),
        )
        return

    if is_payvandlash_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            section_id=section_db_id,
            nested_flow=NESTED_FLOW_PAYVANDLASH,
        )
        await state.set_state(OrderStates.waiting_nested_section_entry)
        await message.answer(
            _nested_entry_prompt_html(loc, title),
            parse_mode="HTML",
            reply_markup=build_nested_section_entry_keyboard(loc),
        )
        return

    if is_elektrik_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            section_id=section_db_id,
            nested_flow=NESTED_FLOW_ELEKTRIK,
        )
        await state.set_state(OrderStates.waiting_nested_section_entry)
        await message.answer(
            _nested_entry_prompt_html(loc, title),
            parse_mode="HTML",
            reply_markup=build_nested_section_entry_keyboard(loc),
        )
        return

    if is_mebel_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            section_id=section_db_id,
            nested_flow=NESTED_FLOW_MEBEL,
        )
        await state.set_state(OrderStates.waiting_nested_section_entry)
        await message.answer(
            _nested_entry_prompt_html(loc, title),
            parse_mode="HTML",
            reply_markup=build_nested_section_entry_keyboard(loc),
        )
        return

    if is_tv_maishiy_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            section_id=section_db_id,
            nested_flow=NESTED_FLOW_TV_MAISHIY,
        )
        await state.set_state(OrderStates.waiting_nested_section_entry)
        await message.answer(
            _nested_entry_prompt_html(loc, title),
            parse_mode="HTML",
            reply_markup=build_nested_section_entry_keyboard(loc),
        )
        return

    if is_konditsioner_section_title(title):
        await state.update_data(
            service=title,
            section_kind=kind,
            section_id=section_db_id,
            nested_flow=NESTED_FLOW_KONDITSIONER,
        )
        await state.set_state(OrderStates.waiting_nested_section_entry)
        await message.answer(
            _nested_entry_prompt_html(loc, title),
            parse_mode="HTML",
            reply_markup=build_nested_section_entry_keyboard(loc),
        )
        return

    await state.update_data(
        service=title, section_kind=kind, section_id=section_db_id
    )
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
    data = await state.get_data()
    flow = data.get("nested_flow")
    if flow in _FLOWS_WITH_NESTED_ENTRY:
        await state.update_data(nested_l2=None)
        await state.set_state(OrderStates.waiting_nested_section_entry)
        db_title = data.get("service") or ""
        await message.answer(
            _nested_entry_prompt_html(loc, db_title),
            parse_mode="HTML",
            reply_markup=build_nested_section_entry_keyboard(loc),
        )
        return
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

    section_id_fsm = data.get("section_id")
    usta_rows: list[dict] = []

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
            section_id=int(section_id_fsm) if section_id_fsm else None,
            section_kind=section_kind,
            problem=problem,
            lat=float(lat) if lat is not None else None,
            lon=float(lon) if lon is not None else None,
        )
        if section_id_fsm:
            usta_rows = await section_ustas_repo.list_claimed_for_section(
                session, int(section_id_fsm)
            )
        next_kb = await build_services_keyboard(session, loc)

    if section_id_fsm and not usta_rows:
        log.info(
            "Buyurtma #%s: bo'lim_id=%s — bog'langan usta yo'q (pending yoki ustalar qo'shilmagan), ustaga xabar yuborilmaydi",
            order_id,
            section_id_fsm,
        )

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

    body_block = (
        f"{user_line}\n"
        f"Xizmat: {service}\n"
        f"{detail_label}: {problem}\n"
        f"{loc_line}"
    )
    text = f"{header}\n{body_block}"

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
            recipient="admin",
        ),
        name=f"admin_notify_order_{order_id}",
    )

    for ur in usta_rows:
        utg = int(ur["telegram_id"])
        if utg == ADMIN_ID:
            continue
        usta_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Qabul qilish",
                        callback_data=OrderCallback(
                            action="accept",
                            order_id=order_id,
                            suid=int(ur["id"]),
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="❌ Rad etish",
                        callback_data=OrderCallback(
                            action="reject",
                            order_id=order_id,
                            suid=int(ur["id"]),
                        ).pack(),
                    ),
                ]
            ]
        )
        usta_full_name = ur["display_name"]
        usta_text = (
            f"👷 Yangi buyurtma #{order_id}\n"
            f"<b>Usta:</b> {escape(usta_full_name)}\n\n"
            f"{body_block}"
        )
        asyncio.create_task(
            _send_admin_order_notice(
                bot,
                admin_chat_id=utg,
                text=usta_text,
                reply_markup=usta_kb,
                order_id=order_id,
                recipient=f"usta#{ur['id']}",
            ),
            name=f"usta_notify_order_{order_id}_{ur['id']}",
        )


@router.callback_query(OrderCallback.filter(F.action == "accept"))
async def cb_order_accept_usta(
    call: CallbackQuery, callback_data: OrderCallback, bot: Bot
) -> None:
    actor = call.from_user.id if call.from_user else 0
    oid = callback_data.order_id
    suid = callback_data.suid
    if suid <= 0 or oid <= 0:
        await call.answer("Xato", show_alert=True)
        return

    async with get_session_factory()() as session:
        outcome, acc_name, acc_phone = await orders_repo.try_accept_order_by_usta(
            session,
            order_id=oid,
            section_usta_id=suid,
            actor_telegram_id=actor,
        )
        row = await orders_repo.get_order(session, oid)

    if outcome == "bad_usta":
        await call.answer("Bu tugma siz uchun emas.", show_alert=True)
        return
    if outcome in ("bad_order", "bad_section"):
        await call.answer("Buyurtma topilmadi.", show_alert=True)
        return
    if outcome == "race":
        await call.answer(
            "Bu buyurtma boshqa usta tomonidan allaqachon qabul qilingan.",
            show_alert=True,
        )
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            log.exception("Usta xabar tugmalarini olib tashlashda xato")
        return

    if outcome != "ok" or not row:
        await call.answer("Xato", show_alert=True)
        return

    client_id = int(row["client_tg_id"])
    async with get_session_factory()() as session:
        cloc = await users_repo.get_locale(session, client_id)
        if await users_repo.is_registered(session, actor):
            usta_loc = await users_repo.get_locale(session, actor)
        else:
            usta_loc = "uz"

    safe_name = escape(acc_name or "")
    safe_phone = escape(acc_phone or "")
    client_html = t(
        cloc,
        "order.usta_accepted_client",
        name=safe_name,
        phone=safe_phone,
    )
    try:
        await bot.send_message(
            client_id,
            client_html,
            parse_mode="HTML",
        )
    except Exception:
        log.exception("Mijozga usta qabul xabari yuborilmadi order=%s", oid)

    # Usta xabarini yangilash — "Tugatish" tugmasi bilan
    try:
        old_text = call.message.text or call.message.html_text or ""
        status_line = t(usta_loc, "order.usta_accept_status")
        complete_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(usta_loc, "order.complete_btn"),
                        callback_data=OrderCallback(
                            action="complete", order_id=oid, suid=suid
                        ).pack(),
                    )
                ]
            ]
        )
        await call.message.edit_text(
            old_text + f"\n\n{status_line}",
            parse_mode="HTML",
            reply_markup=complete_kb,
        )
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            log.exception("Usta xabar tugmalarini olib tashlashda xato")

    # Adminga qabul qilinganligi haqida xabar
    admin_accepted_text = t(
        "uz",
        "order.admin_usta_accepted",
        oid=str(oid),
        name=safe_name,
        phone=safe_phone,
    )
    asyncio.create_task(
        _send_admin_order_notice(
            bot,
            admin_chat_id=ADMIN_ID,
            text=admin_accepted_text,
            reply_markup=None,
            order_id=oid,
            recipient="admin (accept notify)",
        ),
        name=f"admin_accept_notify_{oid}",
    )

    await call.answer(
        t(usta_loc, "order.usta_accept_ok_toast"),
        show_alert=True,
    )


@router.callback_query(OrderCallback.filter(F.action == "complete"))
async def cb_order_complete_usta(
    call: CallbackQuery, callback_data: OrderCallback, bot: Bot
) -> None:
    actor = call.from_user.id if call.from_user else 0
    oid = callback_data.order_id
    suid = callback_data.suid

    async with get_session_factory()() as session:
        ok, row = await orders_repo.complete_order(
            session,
            order_id=oid,
            actor_telegram_id=actor,
            admin_id=ADMIN_ID,
        )

    if not ok or not row:
        await call.answer("Buyurtma yakunlanmadi (allaqachon tugagan yoki ruxsat yo'q).", show_alert=True)
        return

    client_id = int(row["client_tg_id"])
    usta_name = escape(row.get("accepted_usta_name") or "")
    usta_phone = escape(row.get("accepted_usta_phone") or "")

    # Usta xabarida "Tugatish" tugmasini olib tashlash
    try:
        old_text = call.message.text or call.message.html_text or ""
        await call.message.edit_text(
            old_text + "\n\n🏁 <b>Yakunlandi</b>",
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    # Mijozga baholash so'rovi
    async with get_session_factory()() as session:
        cloc = await users_repo.get_locale(session, client_id)

    rate_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{i} ⭐",
                    callback_data=OrderCallback(
                        action="rate",
                        order_id=oid,
                        suid=int(row.get("accepted_usta_id") or suid),
                        rating=i,
                    ).pack(),
                )
                for i in range(1, 6)
            ]
        ]
    )
    try:
        await bot.send_message(
            client_id,
            t(cloc, "order.rate_prompt"),
            reply_markup=rate_kb,
            parse_mode="HTML",
        )
    except Exception:
        log.exception("Mijozga baholash so'rovi yuborilmadi order=%s", oid)

    # Adminga yakunlandi xabari
    admin_text = t(
        "uz",
        "order.admin_completed",
        oid=str(oid),
        name=usta_name,
        phone=usta_phone,
    )
    asyncio.create_task(
        _send_admin_order_notice(
            bot,
            admin_chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=None,
            order_id=oid,
            recipient="admin (complete notify)",
        ),
        name=f"admin_complete_notify_{oid}",
    )

    await call.answer("✅ Yakunlandi!", show_alert=False)


@router.callback_query(OrderCallback.filter(F.action == "rate"))
async def cb_order_rate(
    call: CallbackQuery, callback_data: OrderCallback, bot: Bot
) -> None:
    actor = call.from_user.id if call.from_user else 0
    oid = callback_data.order_id
    suid = callback_data.suid
    rating = callback_data.rating

    if rating < 1 or rating > 5:
        await call.answer("Noto'g'ri baho.", show_alert=True)
        return

    async with get_session_factory()() as session:
        ok, row = await orders_repo.set_order_rating(
            session,
            order_id=oid,
            client_tg_id=actor,
            rating=rating,
        )
        if not ok:
            await call.answer("Baho qabul qilinmadi (avval berilgan yoki ruxsat yo'q).", show_alert=True)
            return
        # Ustaning reytingini yangilash
        if suid > 0:
            await section_ustas_repo.add_rating(session, usta_id=suid, rating=rating)
        # Usta ma'lumotlari (admin xabari uchun)
        usta_row = await section_ustas_repo.get_by_id(session, suid) if suid > 0 else None
        cloc = await users_repo.get_locale(session, actor)

    usta_name = escape(usta_row.first_name + " " + (usta_row.last_name or "") if usta_row else (row or {}).get("accepted_usta_name") or "")

    # Mijozdan baholash tugmalarini olib tashlash + rahmat
    try:
        await call.message.edit_text(
            t(cloc, "order.rate_thanks", rating=str(rating)),
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    # Adminga baho haqida xabar
    admin_rated_text = t(
        "uz",
        "order.admin_rated",
        oid=str(oid),
        rating=str(rating),
        name=usta_name.strip(),
    )
    asyncio.create_task(
        _send_admin_order_notice(
            bot,
            admin_chat_id=ADMIN_ID,
            text=admin_rated_text,
            reply_markup=None,
            order_id=oid,
            recipient="admin (rating notify)",
        ),
        name=f"admin_rating_notify_{oid}",
    )

    await call.answer()


@router.callback_query(OrderCallback.filter(F.action == "reject"))
async def cb_order_reject_usta(
    call: CallbackQuery, callback_data: OrderCallback, state: FSMContext
) -> None:
    """Usta buyurtmani rad etish tugmasini bosdi — sabab so'raydi."""
    actor = call.from_user.id if call.from_user else 0
    oid = callback_data.order_id
    suid = callback_data.suid

    if suid <= 0 or oid <= 0:
        await call.answer("Xato", show_alert=True)
        return

    # Ustaning tegishliligini tekshirish
    async with get_session_factory()() as session:
        su = await session.get(SectionUsta, suid)
        if not su or su.telegram_id != actor:
            await call.answer("Bu tugma siz uchun emas.", show_alert=True)
            return
        order = await orders_repo.get_order(session, oid)
        if not order or order["status"] != "new":
            await call.answer("Buyurtma topilmadi yoki allaqachon qabul qilingan.", show_alert=True)
            try:
                await call.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            return

    # FSM ga order_id, suid, message_id saqlaymiz
    await state.set_state(UstaRejectStates.waiting_reason)
    await state.update_data(
        reject_order_id=oid,
        reject_suid=suid,
        reject_msg_id=call.message.message_id,
        reject_chat_id=call.message.chat.id,
    )

    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await call.message.answer(
        f"❌ Buyurtma #{oid} — rad etish sababini yozing:\n"
        f"(Sabab adminga yuboriladi va admin boshqa ustaga berishi mumkin)"
    )
    await call.answer()


@router.message(UstaRejectStates.waiting_reason)
async def reject_reason_received(message: Message, state: FSMContext, bot: Bot) -> None:
    """Usta sabab matnini yubordi — adminga xabar, ustaga tasdiqlash."""
    if not message.text or not message.text.strip():
        await message.answer("Sabab bo'sh bo'lishi mumkin emas. Matn kiriting:")
        return

    data = await state.get_data()
    oid: int = data.get("reject_order_id", 0)
    suid: int = data.get("reject_suid", 0)
    await state.clear()

    reason = message.text.strip()
    actor = message.from_user.id if message.from_user else 0

    # Usta ma'lumotlarini olish
    async with get_session_factory()() as session:
        su = await session.get(SectionUsta, suid)
        usta_name = f"{su.first_name} {su.last_name or ''}".strip() if su else f"Usta #{suid}"

    # Ustaga tasdiqlash
    await message.answer(
        f"✅ Sababingiz adminga yuborildi. Rahmat!\n"
        f"Buyurtma #{oid} rad etildi."
    )

    # Adminga xabar — "boshqa ustaga berish" tugmasi bilan
    admin_text = (
        f"❌ <b>Buyurtma #{oid} rad etildi</b>\n\n"
        f"👷 Usta: {escape(usta_name)}\n"
        f"📝 Sabab: {escape(reason)}\n\n"
        f"Boshqa ustaga tayinlash uchun quyidagi tugmani bosing:"
    )
    assign_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👷 Boshqa ustaga berish",
                    callback_data=OrderCallback(
                        action="assign_pick", order_id=oid
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Buyurtmani ko'rish",
                    callback_data=OrderCallback(action="view", order_id=oid).pack(),
                )
            ],
        ]
    )

    asyncio.create_task(
        _send_admin_order_notice(
            bot,
            admin_chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=assign_kb,
            order_id=oid,
            recipient="admin (reject notify)",
        ),
        name=f"admin_reject_notify_{oid}_{actor}",
    )
