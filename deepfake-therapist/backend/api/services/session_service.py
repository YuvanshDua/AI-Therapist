"""Database-backed session and message management."""

from __future__ import annotations

from typing import Iterable

from django.utils import timezone

from api.models import Message, TherapySession


class SessionService:
    """Handles create/update/read operations for therapy sessions."""

    @staticmethod
    def start_session(metadata: dict | None = None) -> TherapySession:
        return TherapySession.objects.create(metadata=metadata or {})

    @staticmethod
    def end_session(session: TherapySession) -> TherapySession:
        session.status = TherapySession.SessionStatus.ENDED
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at", "updated_at"])
        return session

    @staticmethod
    def add_message(
        session: TherapySession,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> Message:
        return Message.objects.create(
            session=session,
            role=role,
            content=content,
            metadata=metadata or {},
        )

    @staticmethod
    def get_recent_messages(session: TherapySession, limit: int) -> list[Message]:
        messages = list(session.messages.order_by("-created_at")[:limit])
        messages.reverse()
        return messages

    @staticmethod
    def serialize_messages(messages: Iterable[Message]) -> list[dict]:
        return [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "metadata": message.metadata,
                "timestamp": message.created_at.isoformat(),
            }
            for message in messages
        ]
