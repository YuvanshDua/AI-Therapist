"""Phase-2 vision hooks (stub only for MVP)."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class VisualSignals:
    face_detected: bool = True
    looking_away: bool = False
    low_light: bool = False
    user_present: bool = True


class VisionService:
    """Placeholder service for future webcam frame analysis."""

    def analyze_frame(self, _frame_bytes: bytes) -> dict:
        # TODO(phase-2): plug in real CV model and return measured values.
        return asdict(VisualSignals())
