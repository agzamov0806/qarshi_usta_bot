"""Inline callback ma'lumotlari."""

from aiogram.filters.callback_data import CallbackData


class OrderCallback(CallbackData, prefix="ord"):
    action: str
    order_id: int


class AdminCallback(CallbackData, prefix="adm"):
    action: str


class SectionCallback(CallbackData, prefix="sec"):
    action: str  # menu, list, add, edit, del, dely, toggle, kind
    sid: int = 0


class SectionKindCallback(CallbackData, prefix="sck"):
    sid: int
    kind: str
