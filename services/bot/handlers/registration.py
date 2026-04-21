"""Ro'yxatdan o'tish, til tanlash va /start."""

from html import escape

from aiogram import F
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from packages.db.repositories import users as users_repo
from packages.db.session import get_session_factory
from services.bot.filters import ActiveSectionTitleFilter
from services.bot.i18n import (
    BTN_LANG_RU,
    BTN_LANG_UZ,
    BTN_OPEN_LANGUAGE_MENU,
    LANG_RU,
    LANG_UZ,
    t,
)
from services.bot.keyboards import (
    build_services_keyboard,
    contact_keyboard,
    language_reply_keyboard,
)
from services.bot.router import router
from services.bot.states import LanguageStates, RegStates
from shared.config import get_settings

settings = get_settings()
ADMIN_ID = settings.admin_chat_id

_ONBOARDING_LOCALE_KEY = "onboarding_locale"


def _onboarding_locale_from_data(data: dict) -> str:
    loc = data.get(_ONBOARDING_LOCALE_KEY)
    if loc in (LANG_UZ, LANG_RU):
        return loc
    return LANG_UZ


async def _locale(uid: int) -> str:
    async with get_session_factory()() as session:
        return await users_repo.get_locale(session, uid)


async def show_main_menu(
    message: Message, state: FSMContext, locale: str | None = None
) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else 0
    loc = locale if locale is not None else await _locale(uid)
    extra = ""
    if message.from_user and message.from_user.id == ADMIN_ID:
        extra = t(loc, "main.welcome_admin")
    else:
        extra = t(loc, "main.welcome_lang")
    async with get_session_factory()() as session:
        kb = await build_services_keyboard(session, loc)
    await message.answer(
        t(loc, "main.welcome") + extra,
        reply_markup=kb,
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else 0
    if uid == ADMIN_ID:
        await show_main_menu(message, state)
        return
    async with get_session_factory()() as session:
        if await users_repo.is_registered(session, uid):
            await show_main_menu(message, state)
            return
    await state.set_state(LanguageStates.picking)
    await message.answer(
        t(LANG_UZ, "lang.choose"),
        parse_mode="HTML",
        reply_markup=language_reply_keyboard(),
    )


async def open_language_picker(message: Message, state: FSMContext) -> None:
    """Ro'yxatdan o'tgan foydalanuvchi yoki admin uchun til tanlash ekrani."""
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale(uid)
    if uid != ADMIN_ID:
        async with get_session_factory()() as session:
            if not await users_repo.is_registered(session, uid):
                await message.answer(t(loc, "reg.need_register"))
                return
    await state.set_state(LanguageStates.picking)
    await message.answer(
        t(loc, "lang.choose"),
        parse_mode="HTML",
        reply_markup=language_reply_keyboard(),
    )


@router.message(F.text == BTN_OPEN_LANGUAGE_MENU, StateFilter(None))
async def main_menu_language_button(message: Message, state: FSMContext) -> None:
    await open_language_picker(message, state)


@router.message(or_f(Command("lang"), Command("til")))
async def cmd_change_lang(message: Message, state: FSMContext) -> None:
    await open_language_picker(message, state)


@router.message(LanguageStates.picking, F.text.in_([BTN_LANG_UZ, BTN_LANG_RU]))
async def language_selected(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    new_loc = LANG_RU if message.text == BTN_LANG_RU else LANG_UZ
    async with get_session_factory()() as session:
        registered = await users_repo.is_registered(session, uid)
        if registered:
            await users_repo.set_locale(session, uid, new_loc)
    if registered:
        which = t(new_loc, "lang.which_ru" if new_loc == LANG_RU else "lang.which_uz")
        await message.answer(
            t(new_loc, "lang.changed", which=which),
            reply_markup=ReplyKeyboardRemove(),
        )
        await show_main_menu(message, state, locale=new_loc)
    else:
        await state.update_data(**{_ONBOARDING_LOCALE_KEY: new_loc})
        await state.set_state(RegStates.waiting_first_name)
        await message.answer(
            f"<b>{t(new_loc, 'reg.title')}</b>\n\n{t(new_loc, 'reg.step1')}",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(LanguageStates.picking, ActiveSectionTitleFilter())
async def section_while_language_picking(message: Message, state: FSMContext) -> None:
    """Til tanlash ekranida bo'lim tugmasi bosilsa — til rejimidan chiqib xizmatga o'tamiz."""
    await state.clear()
    from services.bot.handlers.orders import service_chosen

    await service_chosen(message, state)


@router.message(LanguageStates.picking, F.text)
async def language_invalid(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    loc = await _locale(uid)
    await message.answer(
        t(loc, "lang.hint"),
        reply_markup=language_reply_keyboard(),
    )


@router.message(RegStates.waiting_first_name, F.text)
async def reg_first_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    loc = _onboarding_locale_from_data(data)
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer(t(loc, "reg.err_name_short"))
        return
    if len(name) > 64:
        await message.answer(t(loc, "reg.err_name_long"))
        return
    await state.update_data(reg_first=name)
    await state.set_state(RegStates.waiting_last_name)
    await message.answer(t(loc, "reg.step2"), parse_mode="HTML")


@router.message(RegStates.waiting_first_name)
async def reg_first_bad(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    loc = _onboarding_locale_from_data(data)
    await message.answer(t(loc, "reg.err_text_name"))


@router.message(RegStates.waiting_last_name, F.text)
async def reg_last_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    loc = _onboarding_locale_from_data(data)
    fam = (message.text or "").strip()
    if len(fam) < 2:
        await message.answer(t(loc, "reg.err_fam_short"))
        return
    if len(fam) > 64:
        await message.answer(t(loc, "reg.err_name_long"))
        return
    await state.update_data(reg_last=fam)
    await state.set_state(RegStates.waiting_phone)
    await message.answer(
        t(loc, "reg.step3"),
        parse_mode="HTML",
        reply_markup=contact_keyboard(loc),
    )


@router.message(RegStates.waiting_last_name)
async def reg_last_bad(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    loc = _onboarding_locale_from_data(data)
    await message.answer(t(loc, "reg.err_text_fam"))


@router.message(RegStates.waiting_phone, F.contact)
async def reg_phone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    loc_pre = _onboarding_locale_from_data(data)
    c = message.contact
    if not c or not message.from_user:
        return
    if c.user_id and c.user_id != message.from_user.id:
        await message.answer(t(loc_pre, "reg.err_contact_self"))
        return
    first = data.get("reg_first", "").strip()
    last = data.get("reg_last", "").strip()
    if not first or not last:
        await state.clear()
        await message.answer(t(loc_pre, "reg.err_session"))
        return
    async with get_session_factory()() as session:
        await users_repo.save_user(
            session,
            telegram_id=message.from_user.id,
            first_name=first,
            last_name=last,
            phone=c.phone_number,
            locale=loc_pre,
        )
    name_esc = escape(f"{first} {last}")
    await message.answer(
        t(loc_pre, "reg.done", name=name_esc),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await show_main_menu(message, state, locale=loc_pre)


@router.message(RegStates.waiting_phone)
async def reg_phone_hint(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    loc = _onboarding_locale_from_data(data)
    await message.answer(t(loc, "reg.err_contact_only"))
