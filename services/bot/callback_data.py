"""Inline callback ma'lumotlari."""

from aiogram.filters.callback_data import CallbackData


class OrderCallback(CallbackData, prefix="ord"):
    action: str  # view, done, accept, reject, client_complete, client_confirm_yes, client_confirm_no, rate, ...
    order_id: int
    suid: int = 0  # section_ustas.id — accept/reject/rate/assign_usta
    rating: int = 0  # action=rate uchun: 1-5


class AdminCallback(CallbackData, prefix="adm"):
    action: str


class SectionCallback(CallbackData, prefix="sec"):
    action: str  # menu, list, add, edit, del, dely, toggle, kind, usta (ustalar ro'yxati)
    sid: int = 0


class SectionKindCallback(CallbackData, prefix="sck"):
    sid: int
    kind: str


class SectionUstaCallback(CallbackData, prefix="sut"):
    action: str  # add, del, menu
    sid: int
    uid: int = 0  # section_ustas.id — del
