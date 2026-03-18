"""Ollama integration for therapy response and summary updates."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

THERAPIST_SYSTEM_PROMPT = """You are a supportive AI therapy companion for conversational wellness check-ins.
Follow these rules in every reply:
- Calm, warm, supportive tone.
- Keep responses brief and easy to speak aloud (2-4 short sentences).
- Reflect the user's emotion before giving a suggestion.
- Ask at most one gentle question at a time.
- Do not diagnose conditions or claim professional licensure.
- Avoid robotic wording.
- If risk is high, encourage contacting real-world trusted people and emergency or licensed support.
"""

SUMMARY_PROMPT = """Summarize this therapy conversation context in <= 120 words.
Focus on: user emotions, key stressors, coping steps discussed, and open concerns.
Write plain text only.
"""


class OllamaServiceError(RuntimeError):
    """Raised when Ollama calls fail."""


_memory_blocked = False


class OllamaService:
    """Local Ollama API client."""

    def __init__(self) -> None:
        self.enabled = getattr(settings, "OLLAMA_ENABLED", True)
        self.base_url = getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = getattr(settings, "OLLAMA_MODEL", "llama3.2:1b")
        self.timeout = getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 120)
        self.temperature = getattr(settings, "OLLAMA_TEMPERATURE", 0.6)
        self.num_predict = getattr(settings, "OLLAMA_NUM_PREDICT", 220)

    def _chat(self, messages: list[dict[str, str]], num_predict: int | None = None) -> str:
        global _memory_blocked

        if not self.enabled:
            raise OllamaServiceError("Ollama disabled by configuration")
        if _memory_blocked:
            raise OllamaServiceError("Ollama unavailable: model blocked due to low system memory")

        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": messages,
            "options": {
                "temperature": self.temperature,
                "num_predict": num_predict if num_predict is not None else self.num_predict,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = exc.response.text
            except Exception:  # pragma: no cover - defensive
                detail = ""
            if "requires more system memory" in detail.lower():
                _memory_blocked = True
                logger.warning("Ollama disabled for this process due to low memory: %s", detail)
                raise OllamaServiceError(
                    "Ollama model could not load due to low system memory. "
                    "Free RAM/swap or use a smaller model, then restart backend."
                ) from exc
            raise OllamaServiceError(f"Ollama unavailable: {exc}") from exc
        except httpx.HTTPError as exc:
            raise OllamaServiceError(f"Ollama unavailable: {exc}") from exc

        data = response.json()
        message = (data.get("message") or {}).get("content", "")
        text = (message or "").strip()
        if not text:
            raise OllamaServiceError("Ollama returned an empty response")
        return text

    def generate_reply(
        self,
        latest_user_text: str,
        rolling_summary: str,
        recent_messages: list[dict[str, str]],
    ) -> str:
        messages: list[dict[str, str]] = [{"role": "system", "content": THERAPIST_SYSTEM_PROMPT}]

        if rolling_summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"Session summary so far: {rolling_summary}",
                }
            )

        for item in recent_messages:
            role = item.get("role")
            if role not in {"user", "assistant", "system"}:
                continue
            content = (item.get("content") or "").strip()
            if content:
                messages.append({"role": role, "content": content})

        if not recent_messages or (recent_messages and recent_messages[-1].get("content") != latest_user_text):
            messages.append({"role": "user", "content": latest_user_text})

        return self._chat(messages)

    def summarize_context(self, current_summary: str, messages_to_summarize: list[dict[str, str]]) -> str:
        if not messages_to_summarize:
            return current_summary

        transcript_lines = [f"{m['role']}: {m['content']}" for m in messages_to_summarize if m.get("content")]
        if not transcript_lines:
            return current_summary

        messages = [
            {"role": "system", "content": SUMMARY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Previous summary:\n{current_summary or 'None'}\n\n"
                    f"Recent conversation:\n" + "\n".join(transcript_lines)
                ),
            },
        ]

        try:
            return self._chat(messages, num_predict=180)
        except OllamaServiceError as exc:
            logger.warning("Summary update failed, using fallback summary: %s", exc)
            merged = " ".join(transcript_lines)
            return (f"{current_summary} {merged}".strip())[-getattr(settings, "THERAPY_SUMMARY_MAX_CHARS", 1200):]
