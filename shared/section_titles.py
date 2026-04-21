"""
DB da bo'lim nomi bitta qatorda saqlanadi (odatda o'zbekcha, Section.title).

Asosiy menyu ReplyKeyboard matnini tilga bog'lash: ruscha tugma bosilganda
shu yerdagi RU→UZ xaritasi orqali qidiruv Section.title bo'yicha bajariladi.
"""

from __future__ import annotations

# Standart seed (packages.db.repositories.sections.seed_defaults_if_empty) bilan mos
UZ_TO_RU: dict[str, str] = {
    "Santexnika": "Сантехника",
    "Elektrik": "Электрика",
    "Konditsioner": "Кондиционер",
    "Payvandlash xizmati (svarka)": "Сварочные работы",
    "Mebel yig'ish xizmati": "Сборка мебели",
    "Televizor va boshqa maishiy texnika ta'miri": "Ремонт ТВ и бытовой техники",
    "Takliflar": "Предложения",
    "Adminga murojaat": "Связь с администратором",
}

RU_TO_UZ: dict[str, str] = {ru: uz for uz, ru in UZ_TO_RU.items()}


def canonical_title_for_lookup(user_text: str) -> str:
    """Foydalanuvchi yuborgan tugma matni -> DB dagi title (ixcham shakl)."""
    t = user_text.strip()
    return RU_TO_UZ.get(t, t)


def display_title_for_locale(db_title: str, locale: str) -> str:
    """Klaviaturada ko'rinadigan yozuv: uz | ru."""
    loc = (locale or "uz").strip().lower()
    if loc == "ru":
        return UZ_TO_RU.get(db_title, db_title)
    return db_title
