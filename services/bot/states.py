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
    waiting_sub_service = State()
    waiting_sub_detail = State()
    waiting_problem = State()
    waiting_location_choice = State()


class SectionAdminStates(StatesGroup):
    waiting_new_title = State()
    waiting_edit_title = State()
