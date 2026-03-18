"""Rolling memory builder and updater."""

from __future__ import annotations

from django.conf import settings

from api.models import TherapySession
from api.services.session_service import SessionService


class MemoryService:
    """Maintains short-term memory via recent turns + rolling summary."""

    def __init__(self) -> None:
        self.recent_limit = getattr(settings, "THERAPY_RECENT_MESSAGE_LIMIT", 8)
        self.summary_interval = getattr(settings, "THERAPY_SUMMARY_INTERVAL", 6)

    def build_context(self, session: TherapySession) -> tuple[str, list[dict[str, str]]]:
        messages = SessionService.get_recent_messages(session, self.recent_limit)
        recent = [{"role": msg.role, "content": msg.content} for msg in messages]
        return session.rolling_summary or "", recent

    def maybe_update_summary(self, session: TherapySession, summarizer) -> bool:
        total_messages = session.messages.count()
        if total_messages == 0 or total_messages % self.summary_interval != 0:
            return False

        batch = SessionService.get_recent_messages(session, self.summary_interval)
        recent = [{"role": msg.role, "content": msg.content} for msg in batch]
        session.rolling_summary = summarizer(session.rolling_summary, recent)
        session.save(update_fields=["rolling_summary", "updated_at"])
        return True
