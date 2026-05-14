"""Telefon raqamini solishtirish va bazada bir xil shaklda saqlash (O‘zbekiston +998)."""


def digits_only(raw: str) -> str:
    return "".join(c for c in (raw or "") if c.isdigit())


def normalize_phone_for_storage(raw: str) -> str:
    """
    Bazada saqlanadigan kalit: faqat raqamlar, mamlakat kodi 998 bilan (masalan 998901234567).
    Telegram contact va admin kiritmasi bir xil kalitga keladi.
    Natija: 12 raqam, 998 bilan boshlanadi yoki bo'sh string.
    """
    d = digits_only(raw)
    if not d:
        return ""

    # 12 raqam, 998 bilan — already canonical
    if len(d) == 12 and d.startswith("998"):
        return d

    # 9 raqam, 9 bilan boshlanadi — add 998
    if len(d) == 9 and d.startswith("9"):
        d = "998" + d
    # 10 raqam, 8 bilan (old format) — 8 ni 998 ga almashtir
    elif len(d) == 10 and d.startswith("8"):
        d = "998" + d[1:]
    # > 12 raqam — oxirgi 12 raqamni olish va 998 bilan tekshirish
    elif len(d) > 12:
        candidate = d[-12:]
        if candidate.startswith("998"):
            d = candidate
        elif d.startswith("998"):
            d = d[:12]
        else:
            d = ""
    else:
        # Boshqa uzunliklar — noto'g'ri
        d = ""

    # Final check: faqat 12 raqam, 998 bilan boshlanadi
    if len(d) == 12 and d.startswith("998"):
        return d
    return ""


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
