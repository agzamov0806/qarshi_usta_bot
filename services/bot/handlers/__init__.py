"""Handler modullari import qilinganda routerga ulanadi.

Tartib: ro'yxatdan o'tish (registration) buyurtma (orders) dan oldin —
FSM holatidagi xabarlar avvalo to'g'ri handlerga tushishi uchun.
Oxirida fallback — hech narsa mos kelmasa foydalanuvchiga /start haqida xabar.
"""

from services.bot.handlers import admin as admin_handlers  # noqa: F401
from services.bot.handlers import registration as registration_handlers  # noqa: F401
from services.bot.handlers import orders as orders_handlers  # noqa: F401
from services.bot.handlers import sections_admin as sections_admin_handlers  # noqa: F401
from services.bot.handlers import fallback as fallback_handlers  # noqa: F401
