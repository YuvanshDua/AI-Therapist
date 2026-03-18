"""Text-to-speech service wrapper for Piper, Coqui, or Edge TTS."""

from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from django.conf import settings


class TTSGenerationError(RuntimeError):
    """Raised when TTS generation fails."""


@dataclass
class TTSResult:
    audio_url: str
    source: str
    format: str = "wav"
    file_path: str = ""


class TTSService:
    """Generate assistant speech and persist under MEDIA_ROOT."""

    def __init__(self) -> None:
        self.engine = getattr(settings, "TTS_ENGINE", "piper")
        self.output_dir = Path(settings.MEDIA_ROOT) / "tts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str, session_id: str | None = None) -> TTSResult:
        safe_text = self._prepare_text(text)
        if not safe_text:
            raise TTSGenerationError("No text provided for TTS")

        audio_format = "mp3" if self.engine == "edge_tts" else "wav"
        filename = f"{session_id or 'session'}_{uuid4().hex}.{audio_format}"
        out_path = self.output_dir / filename

        if self.engine == "coqui":
            self._synthesize_coqui(safe_text, out_path)
            source = "coqui"
        elif self.engine == "edge_tts":
            self._synthesize_edge_tts(safe_text, out_path)
            source = "edge_tts"
        else:
            self._synthesize_piper(safe_text, out_path)
            source = "piper"

        return TTSResult(
            audio_url=f"{settings.MEDIA_URL}tts/{filename}",
            source=source,
            format=audio_format,
            file_path=str(out_path),
        )

    def _synthesize_piper(self, text: str, out_path: Path) -> None:
        piper_bin = getattr(settings, "PIPER_BIN", "piper")
        model_path = getattr(settings, "PIPER_MODEL_PATH", "")
        if not model_path:
            raise TTSGenerationError("PIPER_MODEL_PATH is not configured")

        cmd = [
            piper_bin,
            "--model",
            model_path,
            "--output_file",
            str(out_path),
            "--length-scale",
            str(getattr(settings, "TTS_PIPER_LENGTH_SCALE", 1.08)),
            "--noise-scale",
            str(getattr(settings, "TTS_PIPER_NOISE_SCALE", 0.6)),
            "--noise-w-scale",
            str(getattr(settings, "TTS_PIPER_NOISE_W_SCALE", 0.9)),
            "--sentence-silence",
            str(getattr(settings, "TTS_PIPER_SENTENCE_SILENCE", 0.26)),
            "--volume",
            str(getattr(settings, "TTS_PIPER_VOLUME", 1.0)),
        ]

        try:
            proc = subprocess.run(cmd, input=text, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise TTSGenerationError(f"Piper binary not found: {piper_bin}") from exc

        if proc.returncode != 0:
            raise TTSGenerationError(proc.stderr.strip() or "Piper synthesis failed")

    def _prepare_text(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return ""

        # Normalize whitespace and punctuation spacing so prosody is steadier.
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.replace("—", ", ").replace("–", ", ")
        cleaned = cleaned.replace(" -- ", ", ")
        cleaned = re.sub(r"\s+([,.;!?])", r"\1", cleaned)

        # Ensure utterances usually end with sentence punctuation for natural cadence.
        if cleaned and cleaned[-1] not in ".!?":
            cleaned = f"{cleaned}."

        max_chars = int(getattr(settings, "TTS_MAX_INPUT_CHARS", 800))
        return cleaned[:max_chars].strip()

    def _synthesize_coqui(self, text: str, out_path: Path) -> None:
        try:
            from TTS.api import TTS
        except ImportError as exc:
            raise TTSGenerationError("Coqui TTS not installed. Run: pip install TTS") from exc

        model_name = getattr(settings, "COQUI_MODEL_NAME", "tts_models/en/ljspeech/tacotron2-DDC")
        tts = TTS(model_name)
        tts.tts_to_file(text=text, file_path=str(out_path))

    def _synthesize_edge_tts(self, text: str, out_path: Path) -> None:
        try:
            import edge_tts
        except ImportError as exc:
            raise TTSGenerationError("edge-tts not installed. Run: pip install edge-tts") from exc

        voice = getattr(settings, "EDGE_TTS_VOICE", "en-US-JennyNeural")
        rate = getattr(settings, "EDGE_TTS_RATE", "-2%")
        pitch = getattr(settings, "EDGE_TTS_PITCH", "+0Hz")
        volume = getattr(settings, "EDGE_TTS_VOLUME", "+0%")

        async def _save() -> None:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            await communicate.save(str(out_path))

        try:
            asyncio.run(_save())
        except Exception as exc:
            raise TTSGenerationError(f"edge_tts synthesis failed: {exc}") from exc
