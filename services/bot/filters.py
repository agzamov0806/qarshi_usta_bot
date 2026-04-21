"""Custom filterlar."""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from packages.db.repositories import sections as sections_repo
from packages.db.session import get_session_factory
from shared.section_titles import canonical_title_for_lookup


class ActiveSectionTitleFilter(BaseFilter):
    """Faqat faol bo'lim nomi bo'lsa True (DB: qo'shimcha Section SELECTsiz)."""

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        canonical = canonical_title_for_lookup(message.text.strip())
        async with get_session_factory()() as session:
            titles = await sections_repo.list_active_titles(session)
        return canonical in titles
