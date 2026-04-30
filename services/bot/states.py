"""FSM holatlari."""

from aiogram.fsm.state import State, StatesGroup


class RegStates(StatesGroup):
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_phone = State()


class LanguageStates(StatesGroup):
    """Til tanlash: yangi foydalanuvchi /start, ro'yxatdan keyin /lang yoki «Til / Язык»."""
    picking = State()


class OrderStates(StatesGroup):
    """Ro'yxat + qo'lda matn tanlovi (Santexnika, Elektrik, ...)."""
    waiting_nested_section_entry = State()
    waiting_sub_service = State()
    waiting_sub_detail = State()
    waiting_optional_media = State()  # ixtiyoriy media va lokatsiya/yozma manzil tugmalari (bir bosqich)
    waiting_problem = State()
    waiting_location_choice = State()
    waiting_visit_address_note = State()  # xaritasiz yo'l — faqat yozma manzil


class SectionAdminStates(StatesGroup):
    waiting_new_title = State()
    waiting_edit_title = State()
    # Usta qo'shish: ism → familiya → telefon
    waiting_usta_first_name = State()
    waiting_usta_last_name = State()
    waiting_usta_phone = State()


class UstaClaimStates(StatesGroup):
    """Usta /start usta orqali kiradi, telefon yuboradi — DB bog'lanadi."""
    waiting_contact = State()


class UstaRejectStates(StatesGroup):
    """Usta buyurtmani rad etganda sabab kiritadi."""
    waiting_reason = State()
