"""Telefon raqamini solishtirish va bazada bir xil shaklda saqlash (O‘zbekiston +998)."""


def digits_only(raw: str) -> str:
    return "".join(c for c in (raw or "") if c.isdigit())


def normalize_phone_for_storage(raw: str) -> str:
    """
    Bazada saqlanadigan kalit: faqat raqamlar, mamlakat kodi 998 bilan (masalan 998901234567).
    Telegram contact va admin kiritmasi bir xil kalitga keladi.
    """
    d = digits_only(raw)
    if not d:
        return ""
    if len(d) == 9 and d[0] == "9":
        d = "998" + d
    elif len(d) == 10 and d.startswith("9"):
        d = "998" + d
    elif len(d) == 11 and d.startswith("89"):
        d = "998" + d[1:]
    elif len(d) == 12 and d.startswith("998"):
        pass
    elif len(d) > 12 and d.endswith(""):
        d = d[-12:] if d[-12:-9] == "998" else d
    return d


def format_phone_display(stored: str) -> str:
    """Inson o‘qishi uchun qisqa format."""
    d = digits_only(stored)
    if len(d) == 12 and d.startswith("998"):
        return f"+{d}"
    if stored and stored.startswith("+"):
        return stored
    return f"+{d}" if d else stored


def phones_match(stored_db: str, contact_phone: str) -> bool:
    return normalize_phone_for_storage(stored_db) == normalize_phone_for_storage(
        contact_phone
    )
