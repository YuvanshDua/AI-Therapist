"""Rule-based safety checks and response overrides."""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.conf import settings


CRISIS_PATTERNS = [
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bsuicid(e|al)\b",
    r"\bwant to die\b",
    r"\bself[- ]?harm\b",
    r"\bhurt myself\b",
    r"\bno reason to live\b",
]


@dataclass
class SafetyResult:
    crisis_detected: bool
    reason: str = ""
    override_response: str = ""


class SafetyService:
    """Simple mandatory safety layer for high-risk messages."""

    def __init__(self) -> None:
        self._patterns = [re.compile(pattern, re.IGNORECASE) for pattern in CRISIS_PATTERNS]

    def evaluate_user_message(self, text: str) -> SafetyResult:
        if not text:
            return SafetyResult(crisis_detected=False)

        for pattern in self._patterns:
            if pattern.search(text):
                hotline = getattr(settings, "THERAPY_CRISIS_HOTLINE", "988 (US & Canada)")
                override = (
                    "I'm really glad you told me this. You deserve immediate support right now. "
                    f"Please call or text {hotline} right now, or contact local emergency services if you might act on these thoughts. "
                    "If possible, reach out to a trusted person and stay with them while you get help from a licensed professional."
                )
                return SafetyResult(crisis_detected=True, reason=pattern.pattern, override_response=override)

        return SafetyResult(crisis_detected=False)

    def sanitize_assistant_response(self, text: str) -> str:
        """Remove unsafe framing that implies licensure or diagnosis."""
        if not text:
            return ""

        sanitized = re.sub(r"\bI (am|\'m) a licensed therapist\b", "I'm here to support you", text, flags=re.IGNORECASE)
        sanitized = re.sub(r"\bmy diagnosis is\b", "what I'm hearing is", sanitized, flags=re.IGNORECASE)
        return sanitized.strip()
