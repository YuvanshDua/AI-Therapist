# Voice Therapist MVP (Django + Ollama + Whisper + Piper)

A local-first voice AI therapist web app with a live-call UI.

## What this build includes
- Django + DRF backend with SQLite persistence
- Session/message models (`TherapySession`, `Message`)
- Modular service layer:
  - `api/services/transcription_service.py`
  - `api/services/ollama_service.py`
  - `api/services/tts_service.py`
  - `api/services/safety_service.py`
  - `api/services/memory_service.py`
  - `api/services/vision_service.py` (phase-2 stub)
- Channels WebSocket endpoint for session events: `/ws/session/<session_id>/`
- Voice call UI (Django template + vanilla JS):
  - start/end session
  - mic record/stop (MediaRecorder)
  - webcam preview (display-only)
  - transcript panel
  - AI thinking/speaking indicator
  - audio playback of generated TTS

## API endpoints
- `POST /api/session/start/`
- `POST /api/session/end/`
- `GET /api/session/<session_id>/`
- `POST /api/transcribe/`
- `POST /api/respond/`
- `POST /api/tts/`
- `GET /api/health/`

## Project layout (key files)
- `backend/therapist_project/settings.py`
- `backend/api/models.py`
- `backend/api/views.py`
- `backend/api/urls.py`
- `backend/api/consumers.py`
- `backend/api/routing.py`
- `backend/api/services/`
- `backend/templates/index.html`
- `frontend/src/call.js`
- `frontend/src/call.css`

## Local setup

### 1) Python dependencies
```bash
cd deepfake-therapist/backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Environment config
```bash
cp .env.example .env
# edit .env with your local model/binary paths
```

### 3) Run DB migrations
```bash
python manage.py migrate
```

### 4) Start Django
```bash
python manage.py runserver
```
Open: `http://127.0.0.1:8000`

## Running local model services

### Ollama
```bash
ollama serve
ollama pull llama3.1:8b
```

### Whisper options

#### Option A: faster-whisper (default in code)
- No separate daemon needed.
- Make sure `WHISPER_ENGINE=faster_whisper` in `.env`.

#### Option B: whisper.cpp CLI
```bash
# Example model download (adjust as needed)
# ./models/download-ggml-model.sh base.en
```
Set in `.env`:
- `WHISPER_ENGINE=whisper_cpp`
- `WHISPER_CPP_BIN=<path to whisper-cli>`
- `WHISPER_CPP_MODEL_PATH=<path to ggml model>`
- `FFMPEG_BIN=ffmpeg`

### TTS options

#### Option A: Piper (recommended)
```bash
# install piper binary (system-specific)
# download a piper .onnx voice model
```
Set in `.env`:
- `TTS_ENGINE=piper`
- `PIPER_BIN=<path to piper>`
- `PIPER_MODEL_PATH=<path to .onnx model>`

#### Option B: Coqui
```bash
pip install TTS
```
Set in `.env`:
- `TTS_ENGINE=coqui`
- `COQUI_MODEL_NAME=tts_models/en/ljspeech/tacotron2-DDC`

## Notes
- Safety override is rule-based and activates on self-harm crisis patterns.
- Rolling memory uses `rolling_summary + recent messages` instead of full transcript for each LLM call.
- Webcam frame analysis is intentionally stubbed for phase-2; structured visual signals are exposed in UI placeholders.
