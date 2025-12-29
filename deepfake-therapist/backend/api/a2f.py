"""
Audio2Face (A2F) helpers.

Parses A2F CSV outputs into a compact JSON-friendly format.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _safe_float(value: Optional[str], default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def find_latest_run(base_dir: Path) -> Optional[Path]:
    if not base_dir.exists():
        return None
    candidates: List[Path] = []
    for entry in base_dir.iterdir():
        if not entry.is_dir():
            continue
        if (entry / "animation_frames.csv").exists():
            candidates.append(entry)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def resolve_run_dir(base_dir: Path, run_id: Optional[str]) -> Optional[Path]:
    if run_id:
        run_dir = base_dir / run_id
        if (run_dir / "animation_frames.csv").exists():
            return run_dir
        return None
    return find_latest_run(base_dir)


def _estimate_fps(frames: List[Dict[str, float]]) -> float:
    if len(frames) < 3:
        return 0.0
    deltas = []
    for idx in range(1, min(10, len(frames))):
        dt = frames[idx]["t"] - frames[idx - 1]["t"]
        if dt > 0:
            deltas.append(dt)
    if not deltas:
        return 0.0
    avg_dt = sum(deltas) / len(deltas)
    return round(1.0 / avg_dt, 2) if avg_dt else 0.0


def parse_animation_frames(csv_path: Path) -> List[Dict[str, float]]:
    frames: List[Dict[str, float]] = []
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            t = _safe_float(row.get("timeCode") or row.get("time_code"))
            jaw_open = _safe_float(row.get("blendShapes.JawOpen"))
            smile_left = _safe_float(row.get("blendShapes.MouthSmileLeft"))
            smile_right = _safe_float(row.get("blendShapes.MouthSmileRight"))
            smile = (smile_left + smile_right) / 2.0
            mouth = _clamp(jaw_open * 4.0)
            frames.append({
                "t": t,
                "jaw": jaw_open,
                "mouth": mouth,
                "smile": smile,
            })
    return frames


def _map_emotion(raw_label: str) -> str:
    if raw_label in {"joy", "cheekiness"}:
        return "happy"
    if raw_label in {"sadness", "grief", "pain"}:
        return "concerned"
    if raw_label in {"anger", "fear", "disgust", "outofbreath"}:
        return "concerned"
    if raw_label in {"amazement"}:
        return "thoughtful"
    return "neutral"


def parse_emotions(csv_path: Path) -> List[Dict[str, float]]:
    emotions: List[Dict[str, float]] = []
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            t = _safe_float(row.get("time_code") or row.get("timeCode"))
            values: Dict[str, float] = {}
            for key, value in row.items():
                if key and key.startswith("emotion_values."):
                    label = key.replace("emotion_values.", "")
                    values[label] = _safe_float(value)
            if not values:
                continue
            dominant_raw, intensity = max(values.items(), key=lambda item: item[1])
            emotions.append({
                "t": t,
                "dominant": _map_emotion(dominant_raw),
                "dominant_raw": dominant_raw,
                "intensity": _clamp(intensity * 2.0),
            })
    return emotions


def resolve_audio_path(run_dir: Path) -> Optional[Path]:
    preferred = run_dir / "out.wav"
    if preferred.exists():
        return preferred
    wavs = sorted(run_dir.glob("*.wav"))
    return wavs[0] if wavs else None


def build_a2f_payload(run_dir: Path) -> Dict[str, object]:
    frames = parse_animation_frames(run_dir / "animation_frames.csv")
    emotions_path = run_dir / "a2f_smoothed_emotion_output.csv"
    emotions = parse_emotions(emotions_path) if emotions_path.exists() else []
    audio_path = resolve_audio_path(run_dir)
    audio_url = f"/api/a2f/audio/{run_dir.name}/" if audio_path else ""
    fps = _estimate_fps(frames)
    return {
        "run_id": run_dir.name,
        "audio_url": audio_url,
        "frames": frames,
        "emotions": emotions,
        "fps": fps,
    }
