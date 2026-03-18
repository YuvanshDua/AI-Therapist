"""Database models for voice therapy sessions."""

import uuid
from django.db import models


class TherapySession(models.Model):
    """Represents one therapy call session."""

    class SessionStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=16, choices=SessionStatus.choices, default=SessionStatus.ACTIVE)
    rolling_summary = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"TherapySession<{self.id}> ({self.status})"


class Message(models.Model):
    """A user/assistant/system message stored for a session."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    session = models.ForeignKey(TherapySession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        short = (self.content or "")[:40].replace("\n", " ")
        return f"Message<{self.role}> {short}"
