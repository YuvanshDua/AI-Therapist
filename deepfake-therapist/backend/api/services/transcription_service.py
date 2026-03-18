"""Speech-to-text service wrapper for faster-whisper or whisper.cpp."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    """Raised when transcription fails."""


@dataclass
class TranscriptionResult:
    text: str
    source: str


_FASTER_WHISPER_MODEL = None

_MIME_TO_SUFFIX = {
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
}


def _load_faster_whisper_model():
    global _FASTER_WHISPER_MODEL
    if _FASTER_WHISPER_MODEL is None:
        from faster_whisper import WhisperModel

        _FASTER_WHISPER_MODEL = WhisperModel(
            getattr(settings, "WHISPER_MODEL", "base"),
            device=getattr(settings, "WHISPER_DEVICE", "cpu"),
            compute_type=getattr(settings, "WHISPER_COMPUTE_TYPE", "int8"),
        )
    return _FASTER_WHISPER_MODEL


class TranscriptionService:
    """Transcribe uploaded audio into text."""

    def __init__(self) -> None:
        self.engine = getattr(settings, "WHISPER_ENGINE", "faster_whisper")

    def transcribe(self, uploaded_file) -> TranscriptionResult:
        suffix = self._resolve_suffix(uploaded_file)

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_audio:
            for chunk in uploaded_file.chunks():
                temp_audio.write(chunk)
            input_path = Path(temp_audio.name)

        cleanup_paths = [input_path]
        try:
            if self.engine == "whisper_cpp":
                text = self._transcribe_whisper_cpp(input_path)
                return TranscriptionResult(text=text, source="whisper_cpp")

            stt_path = self._prepare_for_faster_whisper(input_path)
            if stt_path != input_path:
                cleanup_paths.append(stt_path)

            text = self._transcribe_faster_whisper(stt_path)
            return TranscriptionResult(text=text, source="faster_whisper")
        finally:
            for path in cleanup_paths:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Could not cleanup temp file: %s", path)

    def _resolve_suffix(self, uploaded_file) -> str:
        name_suffix = Path(uploaded_file.name or "").suffix.lower()
        if name_suffix in {".webm", ".mp4", ".wav", ".mp3", ".ogg", ".m4a"}:
            return name_suffix

        content_type = str(getattr(uploaded_file, "content_type", "") or "").lower()
        for mime, suffix in _MIME_TO_SUFFIX.items():
            if content_type == mime or content_type.startswith(f"{mime};"):
                return suffix

        return ".webm"

    def _prepare_for_faster_whisper(self, source_path: Path) -> Path:
        if source_path.suffix.lower() == ".wav":
            return source_path
        return self._convert_to_wav(source_path)

    def _transcribe_faster_whisper(self, audio_path: Path) -> str:
        try:
            model = _load_faster_whisper_model()
            segments, _ = model.transcribe(str(audio_path), beam_size=1, vad_filter=True)
        except Exception as exc:
            raise TranscriptionError(f"faster-whisper failed: {exc}") from exc

        text = " ".join(seg.text.strip() for seg in segments if seg.text).strip()
        if not text:
            raise TranscriptionError("No speech detected in audio")
        return text

    def _transcribe_whisper_cpp(self, audio_path: Path) -> str:
        whisper_bin = getattr(settings, "WHISPER_CPP_BIN", "whisper-cli")
        model_path = getattr(settings, "WHISPER_CPP_MODEL_PATH", "")
        if not model_path:
            raise TranscriptionError("WHISPER_CPP_MODEL_PATH is not configured")

        wav_path = self._convert_to_wav(audio_path)
        out_base = wav_path.with_suffix("")
        cmd = [
            whisper_bin,
            "-m",
            model_path,
            "-f",
            str(wav_path),
            "-otxt",
            "-of",
            str(out_base),
        ]

        try:
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise TranscriptionError(f"whisper.cpp binary not found: {whisper_bin}") from exc

        if proc.returncode != 0:
            raise TranscriptionError(f"whisper.cpp failed: {proc.stderr.strip()}")

        text_path = out_base.with_suffix(".txt")
        if not text_path.exists():
            raise TranscriptionError("whisper.cpp did not produce transcript output")

        text = text_path.read_text(encoding="utf-8").strip()
        text_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)

        if not text:
            raise TranscriptionError("No speech detected in audio")
        return text

    def _convert_to_wav(self, source_path: Path) -> Path:
        if source_path.suffix.lower() == ".wav":
            return source_path

        wav_path = source_path.with_suffix(".wav")
        ffmpeg_bin = getattr(settings, "FFMPEG_BIN", "ffmpeg")
        cmd = [
            ffmpeg_bin,
            "-y",
            "-v",
            "error",
            "-fflags",
            "+discardcorrupt",
            "-err_detect",
            "ignore_err",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ]

        try:
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise TranscriptionError(f"ffmpeg not found: {ffmpeg_bin}") from exc

        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
            raise TranscriptionError(f"ffmpeg conversion failed: {detail}")
        if not wav_path.exists() or wav_path.stat().st_size == 0:
            raise TranscriptionError("ffmpeg conversion produced empty audio output")
        return wav_path
