"""Text-to-speech service wrapper for Piper or Coqui TTS."""

from __future__ import annotations

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


class TTSService:
    """Generate assistant speech and persist under MEDIA_ROOT."""

    def __init__(self) -> None:
        self.engine = getattr(settings, "TTS_ENGINE", "piper")
        self.output_dir = Path(settings.MEDIA_ROOT) / "tts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str, session_id: str | None = None) -> TTSResult:
        safe_text = (text or "").strip()
        if not safe_text:
            raise TTSGenerationError("No text provided for TTS")

        filename = f"{session_id or 'session'}_{uuid4().hex}.wav"
        out_path = self.output_dir / filename

        if self.engine == "coqui":
            self._synthesize_coqui(safe_text, out_path)
            source = "coqui"
        else:
            self._synthesize_piper(safe_text, out_path)
            source = "piper"

        return TTSResult(audio_url=f"{settings.MEDIA_URL}tts/{filename}", source=source)

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
        ]

        try:
            proc = subprocess.run(cmd, input=text, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise TTSGenerationError(f"Piper binary not found: {piper_bin}") from exc

        if proc.returncode != 0:
            raise TTSGenerationError(proc.stderr.strip() or "Piper synthesis failed")

    def _synthesize_coqui(self, text: str, out_path: Path) -> None:
        try:
            from TTS.api import TTS
        except ImportError as exc:
            raise TTSGenerationError("Coqui TTS not installed. Run: pip install TTS") from exc

        model_name = getattr(settings, "COQUI_MODEL_NAME", "tts_models/en/ljspeech/tacotron2-DDC")
        tts = TTS(model_name)
        tts.tts_to_file(text=text, file_path=str(out_path))
