"""O‘zbek va rus tillari — foydalanuvchi uchun matnlar."""

from __future__ import annotations

from packages.db.repositories.sections import KIND_ADMIN_CONTACT, KIND_SUGGESTION

LANG_UZ = "uz"
LANG_RU = "ru"

# Til tanlash tugmalari (noyob matn)
BTN_LANG_UZ = "🇺🇿 O'zbekcha"
BTN_LANG_RU = "🇷🇺 Русский"

# Asosiy menyu: tilni ochish (bitta matn — ikkala tilda tushunarli, DB bo'limlari bilan adashmaydi)
BTN_OPEN_LANGUAGE_MENU = "🌐 Til / Язык"

_MSG: dict[str, dict[str, str]] = {
    "uz": {
        "lang.choose": (
            "🌐 <b>Tilni tanlang / Выберите язык</b>\n\n"
            "Keyingi xabarlar tanlangan tilda bo‘ladi.\n"
            "Следующие сообщения будут на выбранном языке.\n\n"
            "/start — asosiy menyu."
        ),
        "lang.changed": "✅ Til saqlandi: {which}.",
        "lang.which_uz": "O‘zbekcha",
        "lang.which_ru": "Русский",
        "lang.hint": "Pastdagi ikkita tugmadan birini tanlang.",
        "main.welcome": "Assalomu alaykum! Qanday xizmat kerak — tugmani tanlang.",
        "main.welcome_admin": "\n\n👤 Admin: /admin — buyurtmalar paneli.\n🌐 Til: /lang yoki /til",
        "main.welcome_lang": "\n\n🌐 Til: pastdagi «Til / Язык» tugmasi yoki /lang, /til",
        "reg.title": "Ro'yxatdan o'tish",
        "reg.step1": "1/3 — <b>Ismingiz</b>ni yozing (masalan: Ali).",
        "reg.step2": "2/3 — <b>Familiyangiz</b>ni yozing (masalan: Karimov).",
        "reg.step3": (
            "3/3 — <b>Telefon raqamingizni ulashing</b> (pastdagi tugma).\n"
            "Faqat o'z raqamingiz — Telegram tekshiradi."
        ),
        "reg.done": "✅ Ro'yxatdan o'tdingiz: <b>{name}</b>",
        "reg.err_name_short": "Ism kamida 2 ta belgidan iborat bo'lsin.",
        "reg.err_name_long": "Juda uzun. Qisqaroq yozing.",
        "reg.err_fam_short": "Familiya kamida 2 ta belgidan iborat bo'lsin.",
        "reg.err_text_name": "Matn bilan ismingizni yozing.",
        "reg.err_text_fam": "Matn bilan familiyangizni yozing.",
        "reg.err_contact_self": (
            "Faqat o'z telefon raqamingizni «ulashish» tugmasi orqali yuboring."
        ),
        "reg.err_contact_only": 'Faqat «📱 Telefon raqamini ulashish» tugmasidan foydalaning.',
        "reg.err_session": "Ma'lumot buzildi. /start dan qayta boshlang.",
        "fallback.no_handler": (
            "Javob chiqmadi yoki sessiya uzildi. /start dan qayta boshlang.\n\n"
            "Agar muammo takrorlansa, bot faqat bitta serverda ishga tushganini tekshiring."
        ),
        "reg.need_register": "Avval /start orqali ro'yxatdan o'ting.",
        "order.need_register": "Avval /start orqali ro'yxatdan o'ting.",
        "order.section_missing": "Bu bo'lim hozir mavjud emas. /start",
        "order.problem_not_text": "Iltimos, muammoni matn bilan yozing.",
        "order.cancel": "Bekor qilindi. /start bilan qayta boshlang.",
        "order.session_bad": "Sessiya yangilandi. Avval /start bilan ro'yxatdan o'ting.",
        "order.session_nested_bad": "Sessiya buzildi. /start dan boshlang.",
        "order.location_prompt": (
            "Joylashuvni yuboring — pastdagi «Lokatsiyani yuborish» tugmasidan foydalaning "
            "(buyurtma uchun majburiy)."
        ),
        "order.location_hint": (
            "Faqat pastdagi tugma orqali joylashuv yuboring (matn emas)."
        ),
        "order.pick_sub": "Iltimos, pastdagi tugmalardan birini tanlang yoki «Bo'limlarga qaytish»ni bosing.",
        "order.pick_detail": "Iltimos, pastdagi tugmalardan birini tanlang yoki «Oldingi qadamga»ni bosing.",
        "order.sub_non_text": "Matn bilan tugmani tanlang yoki «Bo'limlarga qaytish»ni bosing.",
        "order.detail_non_text": "Matn bilan tugmani tanlang yoki «Oldingi qadamga»ni bosing.",
        "order.back_sections": "Bo'limni tanlang.",
        "order.ok_suggestion": (
            "Rahmat! Taklifingiz qabul qilindi.\n\n"
            "Yana xabar yuborish uchun pastdagi bo'limni tanlang."
        ),
        "order.fail_suggestion": (
            "Taklif saqlandi ✅ (№{oid}). Operatorga xabar vaqtincha bormadi.\n\nKeyinroq urinib ko'ring."
        ),
        "order.ok_admin": (
            "Rahmat! Murojaatingiz qabul qilindi. Tez orada bog'lanamiz.\n\n"
            "Yana murojaat uchun pastdagi bo'limni tanlang."
        ),
        "order.fail_admin": (
            "Murojaat saqlandi ✅ (№{oid}). Operatorga xabar vaqtincha bormadi.\n\nKeyinroq urinib ko'ring."
        ),
        "order.ok_order": (
            "Rahmat! Buyurtma qabul qilindi. Tez orada bog'lanamiz.\n\n"
            "Yana buyurtma berish uchun pastdagi xizmatni tanlang."
        ),
        "order.usta_accepted_client": (
            "✅ <b>Buyurtmangiz usta tomonidan qabul qilindi.</b>\n\n"
            "👤 Usta: <b>{name}</b>\n"
            "📞 Telefon: <b>{phone}</b>"
        ),
        "order.usta_accept_ok_toast": "✅ Mijozga xabar yuborildi.",
        "order.usta_accept_status": "✅ <b>Qabul qilindi</b>",
        "order.admin_usta_accepted": (
            "✅ <b>Buyurtma #{oid} qabul qilindi!</b>\n\n"
            "👤 Usta: <b>{name}</b>\n"
            "📞 Telefon: <b>{phone}</b>"
        ),
        "order.complete_btn": "🏁 Tugatish",
        "order.rate_prompt": (
            "⭐ Ustaning ishini baholang:\n"
            "1 — qoniqarsiz · 5 — a'lo"
        ),
        "order.rate_thanks": "Rahmat! Bahoyingiz qabul qilindi: {rating}/5 ⭐",
        "order.admin_completed": (
            "🏁 <b>Buyurtma #{oid} yakunlandi!</b>\n\n"
            "👤 Usta: <b>{name}</b>\n"
            "📞 Telefon: <b>{phone}</b>"
        ),
        "order.admin_rated": (
            "⭐ <b>Buyurtma #{oid} bahosi: {rating}/5</b>\n"
            "👤 Usta: <b>{name}</b>"
        ),
        "usta.claim_welcome": (
            "👷 <b>Usta sifatida botga ulanish</b>\n\n"
            "Telefoningizni tasdiqlash uchun pastdagi tugmani bosing."
        ),
        "usta.claim_contact_btn": "📱 Telefonni tasdiqlash",
        "usta.claim_only_contact": "Iltimos, pastdagi «📱 Telefonni tasdiqlash» tugmasini bosing.",
        "usta.claim_ok": "✅ Tabriklaymiz, <b>{name}</b>! Siz usta sifatida ro'yxatdan o'tdingiz.\nBo'limlaringizga yangi buyurtma kelganda sizga xabar yuboramiz.",
        "usta.claim_not_found": (
            "❌ Bu telefon raqam tizimda topilmadi.\n"
            "Admin sizni qo'shmagandir yoki boshqa raqam ishlatilgan bo'lishi mumkin.\n"
            "Adminga murojaat qiling."
        ),
        "usta.claim_already": "ℹ️ Siz allaqachon bot bilan bog'langansiz.",
        "order.fail_order": (
            "Buyurtma saqlandi ✅ (№{oid}). Operatorga xabar vaqtincha bormadi — "
            "ADMIN_CHAT_ID va bot bilan /start ni tekshiring.\n\n"
            "Yana urinib ko‘rishingiz mumkin — xizmatni tanlang."
        ),
        "prompt.problem": "Muammo yoki vazifa qisqa yozing (bitta xabar).",
        "prompt.suggestion": "Taklifingizni yozing (bitta xabar).",
        "prompt.admin_contact": "Murojaatingizni yozing (bitta xabar).",
        "kb.contact_placeholder": "Tugmani bosing",
        "kb.services_placeholder": "Xizmatni tanlang",
        "kb.no_section": "— bo'lim yo'q —",
        "kb.ph_detail": "Aniq xizmatni tanlang",
        "kb.ph_santex": "Santexnika: turini tanlang",
        "kb.ph_payvand": "Payvandlash: turini tanlang",
        "kb.ph_elek": "Elektrik: turini tanlang",
        "kb.ph_mebel": "Mebel: turini tanlang",
        "kb.ph_tv": "TV / maishiy: turini tanlang",
        "kb.ph_kond": "Konditsioner: turini tanlang",
        "kb.location_placeholder": "Lokatsiyani yuborish tugmasi",
        "btn.send_location": "Lokatsiyani yuborish",
        "btn.contact_share": "📱 Telefon raqamini ulashish",
        "btn.back_sections": "◀️ Bo'limlarga qaytish",
        "btn.back_detail": "◀️ Oldingi qadamga",
        "btn.nested_list": "Ro'yxat bo'yicha qidirish",
        "btn.nested_manual": "Muammoni qo'lda kiritish",
        "order.nested_entry_prompt": (
            "<b>{title}</b>\n\n"
            "Tur va xizmatni ro'yxatdan tanlash yoki muammoni matn bilan yozish — "
            "pastdagi tugmalardan birini tanlang."
        ),
        "order.nested_entry_pick": "Iltimos, pastdagi tugmalardan birini tanlang.",
        "kb.ph_nested_entry": "Ro'yxat yoki qo'lda",
        "flow.santexnika": "<b>Santexnika</b> — xizmat turini tanlang.",
        "flow.payvandlash": "<b>Payvandlash xizmati (svarka)</b> — xizmat turini tanlang.",
        "flow.elektr": "<b>Elektrik</b> — xizmat turini tanlang.",
        "flow.mebel": "<b>Mebel yig'ish xizmati</b> — xizmat turini tanlang.",
        "flow.tv": "<b>Televizor va boshqa maishiy texnika ta'miri</b> — xizmat turini tanlang.",
        "flow.kond": "<b>Konditsioner</b> — xizmat turini tanlang.",
        "nested.l3_prompt": "<b>{title}</b> — aniq xizmatni tanlang.",
    },
    "ru": {
        "lang.choose": (
            "🌐 <b>Выберите язык</b>\n\n"
            "Следующие сообщения будут на выбранном языке.\n\n"
            "/start — главное меню."
        ),
        "lang.changed": "✅ Язык сохранён: {which}.",
        "lang.which_uz": "Oʻzbekcha",
        "lang.which_ru": "Русский",
        "lang.hint": "Выберите одну из двух кнопок ниже.",
        "main.welcome": "Здравствуйте! Какая услуга нужна — выберите кнопку.",
        "main.welcome_admin": (
            "\n\n👤 Админ: /admin — панель заказов.\n🌐 Язык: /lang или /til"
        ),
        "main.welcome_lang": "\n\n🌐 Язык: кнопка «Til / Язык» снизу или /lang, /til",
        "reg.title": "Регистрация",
        "reg.step1": "1/3 — Напишите <b>имя</b> (например: Али).",
        "reg.step2": "2/3 — Напишите <b>фамилию</b> (например: Каримов).",
        "reg.step3": (
            "3/3 — <b>Отправьте номер телефона</b> (кнопка ниже).\n"
            "Только свой номер — Telegram проверит."
        ),
        "reg.done": "✅ Вы зарегистрированы: <b>{name}</b>",
        "reg.err_name_short": "Имя не короче 2 символов.",
        "reg.err_name_long": "Слишком длинно. Короче.",
        "reg.err_fam_short": "Фамилия не короче 2 символов.",
        "reg.err_text_name": "Отправьте имя текстом.",
        "reg.err_text_fam": "Отправьте фамилию текстом.",
        "reg.err_contact_self": "Отправьте только свой номер через кнопку «Поделиться».",
        "reg.err_contact_only": 'Используйте только кнопку «📱 Поделиться номером».',
        "reg.err_session": "Данные сброшены. Начните с /start.",
        "fallback.no_handler": (
            "Ответ не сформирован или сессия сброшена. Начните с /start.\n\n"
            "Если повторяется — убедитесь, что бот запущен в одном экземпляре."
        ),
        "reg.need_register": "Сначала пройдите регистрацию: /start.",
        "order.need_register": "Сначала пройдите регистрацию: /start.",
        "order.section_missing": "Этот раздел сейчас недоступен. /start",
        "order.problem_not_text": "Опишите проблему текстом.",
        "order.cancel": "Отменено. Начните снова с /start.",
        "order.session_bad": "Сессия сброшена. Сначала /start.",
        "order.session_nested_bad": "Сессия сброшена. Начните с /start.",
        "order.location_prompt": (
            "Отправьте геолокацию кнопкой «Отправить местоположение» ниже "
            "(для заказа обязательно)."
        ),
        "order.location_hint": (
            "Отправьте геолокацию только кнопкой ниже (не текстом)."
        ),
        "order.pick_sub": "Выберите кнопку ниже или «Назад к разделам».",
        "order.pick_detail": "Выберите кнопку ниже или «Назад».",
        "order.sub_non_text": "Выберите кнопку или «Назад к разделам».",
        "order.detail_non_text": "Выберите кнопку или «Назад».",
        "order.back_sections": "Выберите раздел.",
        "order.ok_suggestion": (
            "Спасибо! Предложение принято.\n\n"
            "Чтобы отправить ещё — выберите раздел ниже."
        ),
        "order.fail_suggestion": (
            "Предложение сохранено ✅ (№{oid}). Оператору пока не доставлено.\n\nПопробуйте позже."
        ),
        "order.ok_admin": (
            "Спасибо! Обращение принято. Скоро свяжемся.\n\n"
            "Для нового обращения выберите раздел ниже."
        ),
        "order.fail_admin": (
            "Обращение сохранено ✅ (№{oid}). Оператору пока не доставлено.\n\nПопробуйте позже."
        ),
        "order.ok_order": (
            "Спасибо! Заказ принят. Скоро свяжемся.\n\n"
            "Для нового заказа выберите услугу ниже."
        ),
        "order.usta_accepted_client": (
            "✅ <b>Ваш заказ принят мастером.</b>\n\n"
            "👤 Мастер: <b>{name}</b>\n"
            "📞 Телефон: <b>{phone}</b>"
        ),
        "order.usta_accept_ok_toast": "✅ Клиенту отправлено уведомление.",
        "order.usta_accept_status": "✅ <b>Принят</b>",
        "order.admin_usta_accepted": (
            "✅ <b>Заказ #{oid} принят мастером!</b>\n\n"
            "👤 Мастер: <b>{name}</b>\n"
            "📞 Телефон: <b>{phone}</b>"
        ),
        "order.complete_btn": "🏁 Завершить",
        "order.rate_prompt": (
            "⭐ Оцените работу мастера:\n"
            "1 — плохо · 5 — отлично"
        ),
        "order.rate_thanks": "Спасибо! Оценка принята: {rating}/5 ⭐",
        "order.admin_completed": (
            "🏁 <b>Заказ #{oid} завершён!</b>\n\n"
            "👤 Мастер: <b>{name}</b>\n"
            "📞 Телефон: <b>{phone}</b>"
        ),
        "order.admin_rated": (
            "⭐ <b>Оценка заказа #{oid}: {rating}/5</b>\n"
            "👤 Мастер: <b>{name}</b>"
        ),
        "usta.claim_welcome": (
            "👷 <b>Подключение как мастер</b>\n\n"
            "Нажмите кнопку ниже для подтверждения номера телефона."
        ),
        "usta.claim_contact_btn": "📱 Подтвердить телефон",
        "usta.claim_only_contact": "Нажмите кнопку «📱 Подтвердить телефон» ниже.",
        "usta.claim_ok": "✅ Поздравляем, <b>{name}</b>! Вы зарегистрированы как мастер.\nПри новом заказе в ваших разделах вы получите уведомление.",
        "usta.claim_not_found": (
            "❌ Этот номер телефона не найден в системе.\n"
            "Возможно, администратор ещё не добавил вас или использовал другой номер.\n"
            "Свяжитесь с администратором."
        ),
        "usta.claim_already": "ℹ️ Вы уже подключены к боту как мастер.",
        "order.fail_order": (
            "Заказ сохранён ✅ (№{oid}). Оператору пока не доставлено — проверьте ADMIN_CHAT_ID и /start у бота.\n\n"
            "Можно попробовать снова — выберите услугу."
        ),
        "prompt.problem": "Кратко опишите проблему или задачу (одним сообщением).",
        "prompt.suggestion": "Напишите предложение (одним сообщением).",
        "prompt.admin_contact": "Напишите обращение (одним сообщением).",
        "kb.contact_placeholder": "Нажмите кнопку",
        "kb.services_placeholder": "Выберите услугу",
        "kb.no_section": "— нет разделов —",
        "kb.ph_detail": "Выберите услугу",
        "kb.ph_santex": "Сантехника: тип работы",
        "kb.ph_payvand": "Сварка: тип работы",
        "kb.ph_elek": "Электрика: тип работы",
        "kb.ph_mebel": "Мебель: тип работы",
        "kb.ph_tv": "ТВ / техника: тип работы",
        "kb.ph_kond": "Кондиционер: тип работы",
        "kb.location_placeholder": "Кнопка «Отправить местоположение»",
        "btn.send_location": "Отправить геолокацию",
        "btn.contact_share": "📱 Поделиться номером",
        "btn.back_sections": "◀️ К разделам",
        "btn.back_detail": "◀️ Назад",
        "btn.nested_list": "Поиск по списку",
        "btn.nested_manual": "Описать проблему вручную",
        "order.nested_entry_prompt": (
            "<b>{title}</b>\n\n"
            "Выберите тип и услугу из списка или опишите проблему текстом — "
            "нажмите одну из кнопок ниже."
        ),
        "order.nested_entry_pick": "Выберите одну из кнопок ниже.",
        "kb.ph_nested_entry": "Список или текст",
        "flow.santexnika": "<b>Сантехника</b> — выберите тип услуги.",
        "flow.payvandlash": "<b>Сварка</b> — выберите тип услуги.",
        "flow.elektr": "<b>Электрика</b> — выберите тип услуги.",
        "flow.mebel": "<b>Сборка мебели</b> — выберите тип услуги.",
        "flow.tv": "<b>ТВ и бытовая техника</b> — выберите тип услуги.",
        "flow.kond": "<b>Кондиционер</b> — выберите тип услуги.",
        "nested.l3_prompt": "<b>{title}</b> — выберите услугу.",
    },
}


def back_sections_labels() -> tuple[str, str]:
    return (t(LANG_UZ, "btn.back_sections"), t(LANG_RU, "btn.back_sections"))


def back_detail_labels() -> tuple[str, str]:
    return (t(LANG_UZ, "btn.back_detail"), t(LANG_RU, "btn.back_detail"))


def nested_entry_list_labels() -> tuple[str, str]:
    return (t(LANG_UZ, "btn.nested_list"), t(LANG_RU, "btn.nested_list"))


def nested_entry_manual_labels() -> tuple[str, str]:
    return (t(LANG_UZ, "btn.nested_manual"), t(LANG_RU, "btn.nested_manual"))


def t(locale: str, key: str, **kwargs: str | int) -> str:
    loc = locale if locale in _MSG else LANG_UZ
    s = _MSG[loc].get(key) or _MSG[LANG_UZ].get(key) or key
    if kwargs:
        return s.format(**kwargs)
    return s


def problem_prompt_for_locale(locale: str, section_kind: str | None) -> str:
    if section_kind == KIND_SUGGESTION:
        return t(locale, "prompt.suggestion")
    if section_kind == KIND_ADMIN_CONTACT:
        return t(locale, "prompt.admin_contact")
    return t(locale, "prompt.problem")
