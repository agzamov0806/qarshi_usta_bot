"""
Usta bot — ishga tushirish nuqtasi.

Loyiha tuzilmasi:
- services/bot/*   — Telegram bot
- services/api/*   — FastAPI (REST)
- packages/db/*    — SQLAlchemy + repositorylar
- shared/config.py — muhit sozlamalari

  python main.py              — bot (polling)
  uvicorn services.api.main:app --host 0.0.0.0 --port 8000 — API
"""

from __future__ import annotations

import sys
from pathlib import Path

# Loyiha ildizini import yo‘liga qo‘shamiz (packages, services, shared)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.bot.main import main

if __name__ == "__main__":
    main()
