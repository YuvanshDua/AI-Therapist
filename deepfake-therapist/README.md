# MindfulAI – AI Therapist Avatar

A web experience that pairs a calming chat UI with an AI “therapist.” Users can type or speak, get streamed responses from Gemini or a local LLM, hear TTS playback, and see an animated avatar. An optional Audio2Face viewer can play pre-generated lip-sync + emotion data.

---

## Overview
- **Purpose:** Always-available, judgment-free space for light mental-wellness support.
- **Modes:** Text chat, voice input (Web Speech API), voice output (SpeechSynthesis), streaming responses.
- **Providers:** Google Gemini (default) or a local Ollama-compatible model with caching and rate limiting.
- **Avatar:** Image-based avatar with speaking/emotion cues; optional Audio2Face playback for 3D mouth/emotion tracks.
- **Safety:** Clear “not a replacement for therapy” positioning, rate limits, fallback replies when LLM is down.
- **(New) A2F pipeline:** Kick off Audio2Face generation from fresh text (Google TTS → NVIDIA A2F client) when credentials are configured.
- **(New) Sessions:** Server issues/accepts a `session_id` so you can fetch conversation history per session.

---

## Features
- **Conversational core:** REST + WebSocket streaming; fallback template replies if LLM unavailable.
- **Voice pipeline:** Browser STT for input, browser TTS for output with selectable voices, rate/pitch controls.
- **Provider choice:** Switch between Gemini and local LLM per request; user-supplied API key supported.
- **Resilience:** In-memory cache, rate limiter, metrics endpoint, and cooldowns on the client.
- **A2F viewer:** Load latest Audio2Face run (frames + emotions + wav) and drive the avatar with playback controls.

---

## Architecture
- **Frontend:** Vanilla HTML/JS with Tailwind CDN. WebSocket client for streaming, STT/TTS in-browser, avatar animations, Audio2Face playback controls.
- **Backend:** Django + DRF + Channels (ASGI). REST endpoints for dialogue/health/metrics/TTS/A2F; WebSocket consumer for streamed LLM tokens.
- **LLM integration:** Gemini via `google-genai`; optional local model via Ollama-compatible HTTP API. Template fallback to ensure responses.
- **Storage:** No persistent chat storage; SQLite only for Django defaults. A2F output read from a folder path.

---

## API Quick Reference
- `GET /api/health/` – Health status.
- `POST /api/dialogue/` – `{ text, api_key?, provider? }` → `{ response, source, latency_ms }`.
- `GET /api/metrics/` – Request counts, latency stats, rate-limit count.
- `POST /api/tts/` – Uses Google Cloud TTS if credentials set; falls back to browser TTS hint.
- `GET /api/a2f/latest/` – Latest parsed Audio2Face run (frames, emotions, audio URL).
- `GET /api/a2f/audio/<run_id>/` – Stream the generated wav for a run.
- `POST /api/a2f/generate/` – Generate a new Audio2Face run from text (requires A2F creds); returns payload for the new run.
- `GET /api/session/<session_id>/` – Fetch stored conversation turns for that session.
- WebSocket `ws://<host>/ws/stream/` – Send `{ text, api_key?, provider? }`, receive start/token/done events.

---

## Configuration
Set via environment variables (see `backend/.env.example`):
- `GEMINI_API_KEY` / `GEMINI_MODEL` – Gemini access.
- `LLM_PROVIDER` – `gemini` (default) or `local`.
- `LOCAL_LLM_URL`, `LOCAL_LLM_MODEL`, `LOCAL_NUM_PREDICT`, `LOCAL_TEMPERATURE` – Local model settings.
- `RATE_LIMIT_CALLS_PER_MINUTE` – Per-IP throttle.
- `A2F_OUTPUT_DIR` – Folder containing Audio2Face runs (`animation_frames.csv`, optional emotion CSV, wav).
- `A2F_CONFIG_PATH` – YAML config for A2F client (defaults to `config/config_claire.yml` under output dir).
- `A2F_API_KEY`, `A2F_FUNCTION_ID` – Credentials for NVIDIA Audio2Face-3D NIM.
- `A2F_RUN_TIMEOUT` – Seconds to wait for a generation run.
- `CHANNEL_REDIS_URL` – If set, Channels uses Redis instead of in-memory (recommended for production).
- `DJANGO_SECRET_KEY`, `DEBUG` – Standard Django settings.

---

## Run Locally
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # or source venv/bin/activate
pip install -r requirements.txt
set GEMINI_API_KEY=AIza...   # or export on macOS/Linux
python manage.py runserver
# open http://localhost:8000
```

To use a local LLM instead of Gemini, set `LLM_PROVIDER=local` and point `LOCAL_LLM_URL` to your server (Ollama-compatible).

---

## Project Structure (short)
```
backend/
  api/                # REST + WebSocket logic, A2F parsing, LLM helpers
  therapist_project/  # Django/Channels settings
  templates/index.html
  manage.py, requirements.txt
frontend/
  index.html          # Static build served via Django staticfiles
  src/script.js       # Client logic (chat, STT/TTS, WS, A2F UI)
  src/avatar.js       # Avatar animations
Audio2Face-3D-Samples/
  scripts/audio2face_3d_api_client/  # NVIDIA sample client (external)
```

---

## What’s Done vs. Pending
- **Done:** Chat UI with STT/TTS, streaming via Channels, Gemini/local LLM switch, caching + rate limiting, fallback responder, Audio2Face viewer for existing runs, basic health/metrics/TTS endpoints.
- **In progress:** End-to-end Audio2Face generation (now callable via `/api/a2f/generate/` when TTS + NVIDIA creds are set), production hardening hooks (Redis channel layer env), and multi-session history retrieval.

---

## Deployment Notes
- **Static assets:** `python manage.py collectstatic` with `STATIC_ROOT` set; serve via CDN/reverse proxy.
- **ASGI/Channels:** For production, set `CHANNEL_REDIS_URL=redis://host:6379/0` and run with Daphne/Uvicorn + a process manager (and a Redis instance).
- **TLS/Proxy:** Terminate TLS at a reverse proxy (Nginx/Traefik), set `SECURE_PROXY_SSL_HEADER` if needed, and configure `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`.
- **A2F generation:** Install `google-cloud-texttospeech` and the NVIDIA sample dependencies, set `A2F_API_KEY`, `A2F_FUNCTION_ID`, and point `A2F_OUTPUT_DIR` to the A2F client folder so runs land where the viewer expects them.

---

## Testing
- Django tests live in `backend/api/tests.py`. Run: `cd backend && python manage.py test`.
