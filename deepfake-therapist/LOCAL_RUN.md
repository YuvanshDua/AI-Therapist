# Local Run Commands (Voice Therapist MVP)

## 1) Backend setup
```bash
cd deepfake-therapist/backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and set at minimum:
- `OLLAMA_MODEL`
- `WHISPER_ENGINE`
- `TTS_ENGINE`
- local model/binary paths (`PIPER_MODEL_PATH`, `WHISPER_CPP_MODEL_PATH` if used)

## 2) Database
```bash
python manage.py migrate
```

## 3) Start Django app
```bash
python manage.py runserver
```
Open `http://127.0.0.1:8000`

## 4) Run Ollama (new terminal)
```bash
ollama serve
ollama pull llama3.1:8b
```

## 5) STT options

### faster-whisper (default)
No extra process required after `pip install`.

### whisper.cpp
Install whisper.cpp and set:
- `WHISPER_ENGINE=whisper_cpp`
- `WHISPER_CPP_BIN`
- `WHISPER_CPP_MODEL_PATH`
- `FFMPEG_BIN`

## 6) TTS options

### Piper (recommended)
Install piper binary + voice model and set:
- `TTS_ENGINE=piper`
- `PIPER_BIN`
- `PIPER_MODEL_PATH`

### Coqui
```bash
pip install TTS
```
Set `TTS_ENGINE=coqui`.

## 7) Optional tests/check
```bash
python manage.py check
python manage.py test
```
