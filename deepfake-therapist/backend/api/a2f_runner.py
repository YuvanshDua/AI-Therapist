"""
Audio2Face generation pipeline.

1. Synthesize speech to a WAV file (LINEAR16) using Google Cloud TTS.
2. Invoke the NVIDIA sample client to generate blendshape + emotion CSVs and out.wav.
3. Return the newly created run directory path.

This is an opt-in feature gated by environment variables:
- A2F_API_KEY
- A2F_FUNCTION_ID
- A2F_CONFIG_PATH (default: config/config_claire.yml under A2F_OUTPUT_DIR)
"""

import logging
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class A2FGenerationError(Exception):
    """Raised when Audio2Face generation fails."""


def synthesize_wav(text: str, out_path: Path, voice_name: str = "en-US-Neural2-F", speaking_rate: float = 0.95) -> Path:
    """
    Use Google Cloud TTS to synthesize LINEAR16 audio to a wav file.
    """
    try:
        from google.cloud import texttospeech
    except ImportError as exc:
        raise A2FGenerationError("Google Cloud TTS library not installed (pip install google-cloud-texttospeech)") from exc

    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text[:5000])
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", name=voice_name)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        speaking_rate=speaking_rate,
    )
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    out_path.write_bytes(response.audio_content)
    return out_path


def _detect_new_run_dir(base_dir: Path, before: set) -> Optional[Path]:
    new_dirs = [p for p in base_dir.iterdir() if p.is_dir() and p.name not in before]
    if not new_dirs:
        return None
    return max(new_dirs, key=lambda p: p.stat().st_mtime)


def run_nim_client(audio_path: Path, config_path: Path, api_key: str, function_id: str, base_dir: Path, timeout: int = 180) -> Path:
    """
    Call the NVIDIA Audio2Face-3D sample client to generate animation/emotion data.
    """
    if not audio_path.exists():
        raise A2FGenerationError(f"Audio file not found: {audio_path}")
    if not config_path.exists():
        raise A2FGenerationError(f"Config file not found: {config_path}")
    if not api_key:
        raise A2FGenerationError("Missing A2F_API_KEY")
    if not function_id:
        raise A2FGenerationError("Missing A2F_FUNCTION_ID")

    before_dirs = {p.name for p in base_dir.iterdir() if p.is_dir()}
    cmd = [
        sys.executable,
        "nim_a2f_3d_client.py",
        str(audio_path),
        str(config_path),
        "--apikey",
        api_key,
        "--function-id",
        function_id,
    ]
    logger.info("Running Audio2Face client...")
    result = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        logger.error("A2F client failed: %s", result.stderr.strip())
        raise A2FGenerationError(f"A2F client failed: {result.stderr.strip() or result.stdout.strip()}")

    new_dir = _detect_new_run_dir(base_dir, before_dirs)
    if not new_dir:
        raise A2FGenerationError("Audio2Face client finished but no output directory was created")
    logger.info("A2F run completed: %s", new_dir)
    return new_dir


def generate_a2f_run(
    text: str,
    voice_name: str = "en-US-Neural2-F",
    speaking_rate: float = 0.95,
    api_key: str = "",
    function_id: str = "",
    config_path: Optional[Path] = None,
) -> Path:
    """
    High-level pipeline to generate a new Audio2Face run directory.
    """
    base_dir = Path(getattr(settings, "A2F_OUTPUT_DIR", "")).expanduser()
    if not base_dir.exists():
        raise A2FGenerationError(f"A2F_OUTPUT_DIR does not exist: {base_dir}")

    cfg_path = Path(config_path) if config_path else Path(getattr(settings, "A2F_CONFIG_PATH", ""))
    if not cfg_path:
        cfg_path = base_dir / "config" / "config_claire.yml"

    api_key = api_key or getattr(settings, "A2F_API_KEY", "") or ""
    function_id = function_id or getattr(settings, "A2F_FUNCTION_ID", "") or ""

    tmp_audio = base_dir / f"tts_input_{uuid.uuid4().hex}.wav"
    try:
        synthesize_wav(text, tmp_audio, voice_name=voice_name, speaking_rate=speaking_rate)
        new_run = run_nim_client(tmp_audio, cfg_path, api_key, function_id, base_dir)
        return new_run
    finally:
        if tmp_audio.exists():
            try:
                tmp_audio.unlink()
            except OSError:
                logger.debug("Could not clean up temp audio file: %s", tmp_audio)
