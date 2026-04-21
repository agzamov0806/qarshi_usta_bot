"""Reply va inline klaviaturalar."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.repositories import sections as sections_repo
from shared.section_titles import display_title_for_locale
from services.bot.callback_data import AdminCallback
from services.bot.i18n import BTN_OPEN_LANGUAGE_MENU, LANG_RU, LANG_UZ, t
from services.bot.keyboard_ru import (
    ELEKTRIK_DETAIL_BY_SUB_RU,
    ELEKTRIK_SUB_SERVICES_RU,
    KONDITSIONER_DETAIL_BY_SUB_RU,
    KONDITSIONER_SUB_SERVICES_RU,
    MEBEL_DETAIL_BY_SUB_RU,
    MEBEL_SUB_SERVICES_RU,
    PAYVANDLASH_DETAIL_BY_SUB_RU,
    PAYVANDLASH_SUB_SERVICES_RU,
    SANTEXNIKA_DETAIL_BY_SUB_RU,
    SANTEXNIKA_SUB_SERVICES_RU,
    TV_MAISHIY_DETAIL_BY_SUB_RU,
    TV_MAISHIY_SUB_SERVICES_RU,
)

# Bo'lim nomi DB dagi «Santexnika» bilan mos (katta-kichik harf farqi yo'q)
SANTEXNIKA_TITLE_KEY = "santexnika"

# Santexnika ichidagi pastki xizmatlar (ReplyKeyboard)
SANTEXNIKA_SUB_SERVICES: tuple[str, ...] = (
    "Jihozlarni o‘rnatish",
    "Quvur (truba) ishlari",
    "Ta'mirlash va nosozlikni bartaraf qilish",
    "Isitish tizimi ishlari",
    "Qo‘shimcha ishlar",
)

SANTEXNIKA_BACK_BUTTON = "◀️ Bo'limlarga qaytish"

# Ikkinchi bosqichdan keyin — uchinchi bosqich (aniq xizmat)
SANTEXNIKA_DETAIL_BY_SUB: dict[str, tuple[str, ...]] = {
    "Jihozlarni o‘rnatish": (
        "Rakovina (qo‘l yuvgich) o‘rnatish",
        "Unitaz (tualet) o‘rnatish",
        "Dush kabina yoki vanna o‘rnatish",
        "Kran (smesitel) o‘rnatish",
        "Kir yuvish mashinasi ulash",
        "Idish yuvish mashinasi ulash",
    ),
    "Quvur (truba) ishlari": (
        "Sovuq va issiq suv quvurlarini tortish",
        "Kanalizatsiya quvurlarini o‘rnatish",
        "Eski trubalarni almashtirish",
        "Plastik, metall yoki boshqa turdagi quvurlar bilan ishlash",
    ),
    "Ta'mirlash va nosozlikni bartaraf qilish": (
        "Oqayotgan kranlarni tuzatish",
        "Tiqilib qolgan kanalizatsiyani ochish",
        "Suv sizib chiqishini bartaraf qilish",
        "Unitaz yoki rakovinadagi muammolarni tuzatish",
    ),
    "Isitish tizimi ishlari": (
        "Radiator (batareya) o‘rnatish",
        "Qozon (kotel) ulash",
        "Issiq suv tizimini sozlash",
    ),
    "Qo‘shimcha ishlar": (
        "Filtrlar o‘rnatish (suv tozalash uchun)",
        "Nasos (nasos stansiya) ulash",
        "Hisoblagich (suv hisoblagichi) o‘rnatish",
    ),
}

SANTEXNIKA_DETAIL_BACK_BUTTON = "◀️ Oldingi qadamga"

# Payvandlash — DB dagi bo‘lim nomi bilan mos
PAYVANDLASH_TITLE_KEY = "payvandlash xizmati (svarka)"

PAYVANDLASH_SUB_SERVICES: tuple[str, ...] = (
    "Metall konstruksiya yasash",
    "Qurilishdagi og‘ir svarka ishlari",
    "Truba svarkasi",
    "Avto svarka",
    "Boshqalar",
)

PAYVANDLASH_DETAIL_BY_SUB: dict[str, tuple[str, ...]] = {
    "Metall konstruksiya yasash": (
        "Panjara (reshotka)",
        "Zabor (to‘siq)",
        "Navis (tomcha, ayvon usti)",
    ),
    "Qurilishdagi og‘ir svarka ishlari": (
        "Armatura payvandlash",
        "Karkas yig‘ish",
    ),
    "Truba svarkasi": (
        "Metall suv trubalari",
        "Gaz trubalari",
    ),
    "Avto svarka": (
        "Kuzov payvandlash",
        "Egzoz (glushitel) tuzatish",
    ),
    "Boshqalar": (
        "Mayda temir yopishtirish",
        '"aka bir joyini payvandlab ber" ishlar',
    ),
}

# Elektrik — DB dagi bo‘lim «Elektrik»
ELEKTRIK_TITLE_KEY = "elektrik"

ELEKTRIK_SUB_SERVICES: tuple[str, ...] = (
    "To'liq elektr montaj",
    "Yashirin sim tortish (skritiy montaj)",
    '"Smart uy" va zamonaviy tizimlar',
    "Nosozliklarni topish (diagnostika)",
    "Shoshilinch xizmat",
    "Boshqalar",
)

ELEKTRIK_DETAIL_BY_SUB: dict[str, tuple[str, ...]] = {
    "To'liq elektr montaj": (
        "Yangi uy/kvartirada 0 dan sim tortish",
        "Shit (elektr panel) yig‘ish",
        "Avtomatlarni joylashtirish",
        "Simlarni to‘g‘ri taqsimlash",
        "Himoya tizimlari (UZO, differensial)",
    ),
    "Yashirin sim tortish (skritiy montaj)": (
        "Devor ichidan kabel o‘tkazish",
        "Shtroba qilish (devorni kesish)",
    ),
    '"Smart uy" va zamonaviy tizimlar': (
        "Aqlli svet (masofadan boshqarish)",
        "Sensorlar",
        "Kamera va signalizatsiya",
    ),
    "Nosozliklarni topish (diagnostika)": (
        "Qayerda tok yo‘qolganini topish",
        "Qisqa tutashuvni aniqlash",
    ),
    "Shoshilinch xizmat": (
        "Tok yo‘q bo‘lib qolgan",
        "Avtomat urib tashlayapti",
    ),
    "Boshqalar": (
        "Rozetka/almashtirish",
        "Lampochka qo‘yish",
        "Oddiy kichik ishlar",
    ),
}

# Mebel — DB dagi «Mebel yig'ish xizmati»
MEBEL_TITLE_KEY = "mebel yig'ish xizmati"

MEBEL_SUB_SERVICES: tuple[str, ...] = (
    "Oshxona mebeli",
    "O‘rnatish + kesish + moslash",
    "Ofis va katta obyektlar",
    "Eshik, shkaf-kupe o‘rnatish",
    "Boshqalar",
)

MEBEL_DETAIL_BY_SUB: dict[str, tuple[str, ...]] = {
    "Oshxona mebeli": (
        "Kuxnya garnitur yig‘ish",
        "Moyka (rakovina) kesish va o‘rnatish",
        "Plita, vityajka o‘rnatish",
    ),
    "O‘rnatish + kesish + moslash": (
        "Stoleshnitsa kesish",
        "Devorga moslab kesish",
        "Eshiklarni tekislash",
    ),
    "Ofis va katta obyektlar": (
        "Ofis mebellari",
        "Magazin, salon jihozlari",
    ),
    "Eshik, shkaf-kupe o‘rnatish": (
        "Shkaf-kupe (sliding)",
        "Ichki eshiklar",
    ),
    "Boshqalar": (
        "Oddiy tipdagi mebel yig‘ish",
        "1-2 dona shkaf yig‘ish",
        "Mayda ishlar",
    ),
}

# Televizor / maishiy — DB «Televizor va boshqa maishiy texnika ta'miri»
TV_MAISHIY_TITLE_KEY = "televizor va boshqa maishiy texnika ta'miri"

TV_MAISHIY_SUB_SERVICES: tuple[str, ...] = (
    "Televizor diagnostika",
    "Maishiy texnikalar ta'miri",
    "Qo‘shimcha xizmatlar",
)

TV_MAISHIY_DETAIL_BY_SUB: dict[str, tuple[str, ...]] = {
    "Televizor diagnostika": (
        "Nima ishlamayotganini topish",
        "Ekran qorong‘i: ovoz bor, rasm yo‘q",
        "Smart ishlamayapti",
        "TV devorga osish",
        "Antenna ulash",
        "Smart sozlash",
    ),
    "Maishiy texnikalar ta'miri": (
        "Dazmol, elektr choynak va fen",
        "Mikrotulqinli pech (mikrovolnovka)",
        "Kir yuvish mashinasi",
        "Duxovka (220 V / 380 V)",
        "Mikserlar (220 V / 380 V)",
    ),
}

# Konditsioner — DB «Konditsioner»
KONDITSIONER_TITLE_KEY = "konditsioner"

KONDITSIONER_SUB_SERVICES: tuple[str, ...] = (
    "O‘rnatish",
    "Servis va tozalash",
    "Ta'mirlash",
)

KONDITSIONER_DETAIL_BY_SUB: dict[str, tuple[str, ...]] = {
    "O‘rnatish": (
        "Yangi konditsioner o‘rnatish",
        "O‘rnatilgan konditsioner boshqa joyga o‘rnatish",
    ),
    "Servis va tozalash": (
        "Filtr tozalash",
        "Freon tekshirish / zapravka",
    ),
    "Ta'mirlash": (
        "Sovitmayapti",
        "Isitmayapti",
        "Elektr nosozlik",
        "Boshqa",
    ),
}


def is_santexnika_section_title(title: str) -> bool:
    return title.strip().casefold() == SANTEXNIKA_TITLE_KEY


def is_payvandlash_section_title(title: str) -> bool:
    return title.strip().casefold() == PAYVANDLASH_TITLE_KEY


def is_elektrik_section_title(title: str) -> bool:
    return title.strip().casefold() == ELEKTRIK_TITLE_KEY


def is_mebel_section_title(title: str) -> bool:
    return title.strip().casefold() == MEBEL_TITLE_KEY


def is_tv_maishiy_section_title(title: str) -> bool:
    return title.strip().casefold() == TV_MAISHIY_TITLE_KEY


def is_konditsioner_section_title(title: str) -> bool:
    return title.strip().casefold() == KONDITSIONER_TITLE_KEY


def _pick_sub(
    uz_t: tuple[str, ...], ru_t: tuple[str, ...], locale: str
) -> tuple[str, ...]:
    return ru_t if locale == LANG_RU else uz_t


def _pick_detail_map(
    uz_m: dict[str, tuple[str, ...]],
    ru_m: dict[str, tuple[str, ...]],
    locale: str,
) -> dict[str, tuple[str, ...]]:
    return ru_m if locale == LANG_RU else uz_m


# orders.py uchun: flow = nested_flow satri ("santexnika", "elektrik", ...)
def nested_subs_for_flow(flow: str, locale: str) -> tuple[str, ...]:
    if flow == "santexnika":
        return _pick_sub(SANTEXNIKA_SUB_SERVICES, SANTEXNIKA_SUB_SERVICES_RU, locale)
    if flow == "payvandlash":
        return _pick_sub(PAYVANDLASH_SUB_SERVICES, PAYVANDLASH_SUB_SERVICES_RU, locale)
    if flow == "elektrik":
        return _pick_sub(ELEKTRIK_SUB_SERVICES, ELEKTRIK_SUB_SERVICES_RU, locale)
    if flow == "mebel":
        return _pick_sub(MEBEL_SUB_SERVICES, MEBEL_SUB_SERVICES_RU, locale)
    if flow == "tv_maishiy":
        return _pick_sub(TV_MAISHIY_SUB_SERVICES, TV_MAISHIY_SUB_SERVICES_RU, locale)
    if flow == "konditsioner":
        return _pick_sub(KONDITSIONER_SUB_SERVICES, KONDITSIONER_SUB_SERVICES_RU, locale)
    return ()


def nested_detail_map_for_flow(flow: str, locale: str) -> dict[str, tuple[str, ...]]:
    if flow == "santexnika":
        return _pick_detail_map(
            SANTEXNIKA_DETAIL_BY_SUB, SANTEXNIKA_DETAIL_BY_SUB_RU, locale
        )
    if flow == "payvandlash":
        return _pick_detail_map(
            PAYVANDLASH_DETAIL_BY_SUB, PAYVANDLASH_DETAIL_BY_SUB_RU, locale
        )
    if flow == "elektrik":
        return _pick_detail_map(ELEKTRIK_DETAIL_BY_SUB, ELEKTRIK_DETAIL_BY_SUB_RU, locale)
    if flow == "mebel":
        return _pick_detail_map(MEBEL_DETAIL_BY_SUB, MEBEL_DETAIL_BY_SUB_RU, locale)
    if flow == "tv_maishiy":
        return _pick_detail_map(
            TV_MAISHIY_DETAIL_BY_SUB, TV_MAISHIY_DETAIL_BY_SUB_RU, locale
        )
    if flow == "konditsioner":
        return _pick_detail_map(
            KONDITSIONER_DETAIL_BY_SUB, KONDITSIONER_DETAIL_BY_SUB_RU, locale
        )
    return {}


def build_santexnika_sub_keyboard(locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    s = _pick_sub(SANTEXNIKA_SUB_SERVICES, SANTEXNIKA_SUB_SERVICES_RU, locale)
    back = t(locale, "btn.back_sections")
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=s[0]), KeyboardButton(text=s[1])],
        [KeyboardButton(text=s[2]), KeyboardButton(text=s[3])],
        [KeyboardButton(text=s[4])],
        [KeyboardButton(text=back)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_santex"),
    )


def build_santexnika_detail_keyboard(
    parent_sub: str, locale: str = LANG_UZ
) -> ReplyKeyboardMarkup:
    dm = _pick_detail_map(
        SANTEXNIKA_DETAIL_BY_SUB, SANTEXNIKA_DETAIL_BY_SUB_RU, locale
    )
    items = dm.get(parent_sub)
    back = t(locale, "btn.back_sections")
    detail_back = t(locale, "btn.back_detail")
    if not items:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=back)]],
            resize_keyboard=True,
        )
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(items), 2):
        row = [KeyboardButton(text=items[i])]
        if i + 1 < len(items):
            row.append(KeyboardButton(text=items[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text=detail_back)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_detail"),
    )


def build_payvandlash_sub_keyboard(locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    s = _pick_sub(PAYVANDLASH_SUB_SERVICES, PAYVANDLASH_SUB_SERVICES_RU, locale)
    back = t(locale, "btn.back_sections")
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=s[0]), KeyboardButton(text=s[1])],
        [KeyboardButton(text=s[2]), KeyboardButton(text=s[3])],
        [KeyboardButton(text=s[4])],
        [KeyboardButton(text=back)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_payvand"),
    )


def build_payvandlash_detail_keyboard(
    parent_sub: str, locale: str = LANG_UZ
) -> ReplyKeyboardMarkup:
    dm = _pick_detail_map(
        PAYVANDLASH_DETAIL_BY_SUB, PAYVANDLASH_DETAIL_BY_SUB_RU, locale
    )
    items = dm.get(parent_sub)
    back = t(locale, "btn.back_sections")
    detail_back = t(locale, "btn.back_detail")
    if not items:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=back)]],
            resize_keyboard=True,
        )
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(items), 2):
        row = [KeyboardButton(text=items[i])]
        if i + 1 < len(items):
            row.append(KeyboardButton(text=items[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text=detail_back)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_detail"),
    )


def build_elektrik_sub_keyboard(locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    s = _pick_sub(ELEKTRIK_SUB_SERVICES, ELEKTRIK_SUB_SERVICES_RU, locale)
    back = t(locale, "btn.back_sections")
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=s[0]), KeyboardButton(text=s[1])],
        [KeyboardButton(text=s[2]), KeyboardButton(text=s[3])],
        [KeyboardButton(text=s[4]), KeyboardButton(text=s[5])],
        [KeyboardButton(text=back)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_elek"),
    )


def build_elektrik_detail_keyboard(
    parent_sub: str, locale: str = LANG_UZ
) -> ReplyKeyboardMarkup:
    dm = _pick_detail_map(ELEKTRIK_DETAIL_BY_SUB, ELEKTRIK_DETAIL_BY_SUB_RU, locale)
    items = dm.get(parent_sub)
    back = t(locale, "btn.back_sections")
    detail_back = t(locale, "btn.back_detail")
    if not items:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=back)]],
            resize_keyboard=True,
        )
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(items), 2):
        row = [KeyboardButton(text=items[i])]
        if i + 1 < len(items):
            row.append(KeyboardButton(text=items[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text=detail_back)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_detail"),
    )


def build_mebel_sub_keyboard(locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    s = _pick_sub(MEBEL_SUB_SERVICES, MEBEL_SUB_SERVICES_RU, locale)
    back = t(locale, "btn.back_sections")
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=s[0]), KeyboardButton(text=s[1])],
        [KeyboardButton(text=s[2]), KeyboardButton(text=s[3])],
        [KeyboardButton(text=s[4])],
        [KeyboardButton(text=back)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_mebel"),
    )


def build_mebel_detail_keyboard(parent_sub: str, locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    dm = _pick_detail_map(MEBEL_DETAIL_BY_SUB, MEBEL_DETAIL_BY_SUB_RU, locale)
    items = dm.get(parent_sub)
    back = t(locale, "btn.back_sections")
    detail_back = t(locale, "btn.back_detail")
    if not items:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=back)]],
            resize_keyboard=True,
        )
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(items), 2):
        row = [KeyboardButton(text=items[i])]
        if i + 1 < len(items):
            row.append(KeyboardButton(text=items[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text=detail_back)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_detail"),
    )


def build_tv_maishiy_sub_keyboard(locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    s = _pick_sub(TV_MAISHIY_SUB_SERVICES, TV_MAISHIY_SUB_SERVICES_RU, locale)
    back = t(locale, "btn.back_sections")
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=s[0]), KeyboardButton(text=s[1])],
        [KeyboardButton(text=s[2])],
        [KeyboardButton(text=back)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_tv"),
    )


def build_tv_maishiy_detail_keyboard(
    parent_sub: str, locale: str = LANG_UZ
) -> ReplyKeyboardMarkup:
    dm = _pick_detail_map(TV_MAISHIY_DETAIL_BY_SUB, TV_MAISHIY_DETAIL_BY_SUB_RU, locale)
    items = dm.get(parent_sub)
    back = t(locale, "btn.back_sections")
    detail_back = t(locale, "btn.back_detail")
    if not items:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=back)]],
            resize_keyboard=True,
        )
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(items), 2):
        row = [KeyboardButton(text=items[i])]
        if i + 1 < len(items):
            row.append(KeyboardButton(text=items[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text=detail_back)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_detail"),
    )


def build_konditsioner_sub_keyboard(locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    s = _pick_sub(KONDITSIONER_SUB_SERVICES, KONDITSIONER_SUB_SERVICES_RU, locale)
    back = t(locale, "btn.back_sections")
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=s[0]), KeyboardButton(text=s[1])],
        [KeyboardButton(text=s[2])],
        [KeyboardButton(text=back)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_kond"),
    )


def build_konditsioner_detail_keyboard(
    parent_sub: str, locale: str = LANG_UZ
) -> ReplyKeyboardMarkup:
    dm = _pick_detail_map(
        KONDITSIONER_DETAIL_BY_SUB, KONDITSIONER_DETAIL_BY_SUB_RU, locale
    )
    items = dm.get(parent_sub)
    back = t(locale, "btn.back_sections")
    detail_back = t(locale, "btn.back_detail")
    if not items:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=back)]],
            resize_keyboard=True,
        )
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(items), 2):
        row = [KeyboardButton(text=items[i])]
        if i + 1 < len(items):
            row.append(KeyboardButton(text=items[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text=detail_back)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.ph_detail"),
    )


async def build_services_keyboard(
    session: AsyncSession, locale: str = LANG_UZ
) -> ReplyKeyboardMarkup:
    titles = await sections_repo.list_active_titles(session)
    labels = [display_title_for_locale(title, locale) for title in titles]
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(labels), 2):
        row = [KeyboardButton(text=labels[i])]
        if i + 1 < len(labels):
            row.append(KeyboardButton(text=labels[i + 1]))
        rows.append(row)
    if not rows:
        rows = [[KeyboardButton(text=t(locale, "kb.no_section"))]]
    rows.append([KeyboardButton(text=BTN_OPEN_LANGUAGE_MENU)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.services_placeholder"),
    )


def location_request_keyboard(locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    """Joylashuv so‘rovi — faqat «Lokatsiyani yuborish» tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=t(locale, "btn.send_location"),
                    request_location=True,
                ),
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.location_placeholder"),
    )


def contact_keyboard(locale: str = LANG_UZ) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=t(locale, "btn.contact_share"),
                    request_contact=True,
                )
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=t(locale, "kb.contact_placeholder"),
    )


def language_reply_keyboard() -> ReplyKeyboardMarkup:
    from services.bot.i18n import BTN_LANG_RU, BTN_LANG_UZ

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_LANG_UZ), KeyboardButton(text=BTN_LANG_RU)]],
        resize_keyboard=True,
        input_field_placeholder="O'zbekcha / Русский",
    )


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Oxirgi 10 ta buyurtma",
                    callback_data=AdminCallback(action="list").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Qisqa statistika",
                    callback_data=AdminCallback(action="stats").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📂 Bo'limlar (CRUD)",
                    callback_data=AdminCallback(action="sections").pack(),
                )
            ],
        ]
    )
