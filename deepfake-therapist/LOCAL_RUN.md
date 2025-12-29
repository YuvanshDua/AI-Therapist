# MindfulAI - Local Run Guide

This guide will help you run the MindfulAI application on your local machine.

## Quick Start (5 minutes)

### Step 1: Prerequisites

Make sure you have:

- **Python 3.9+** installed ([Download](https://python.org))
- **pip** (comes with Python)
- A **web browser** (Chrome recommended for best Speech API support)

Check your Python version:

```bash
python --version
```

### Step 2: Get Gemini API Key (FREE!)

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with `AIza...`)

**Free Tier Limits:**

- 15 requests per minute
- 1 million tokens per day
- No credit card required!

### Step 3: Setup

Open Command Prompt/Terminal and run:

```bash
# Navigate to project
cd path/to/deepfake-therapist/backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Set API Key

```bash
# Windows Command Prompt:
set GEMINI_API_KEY=AIzaSy...your-key-here

# Windows PowerShell:
$env:GEMINI_API_KEY="AIzaSy...your-key-here"

# macOS/Linux:
export GEMINI_API_KEY=AIzaSy...your-key-here
```

### Step 5: Run Server

```bash
python manage.py runserver
```

### Step 6: Open Application

Open your browser and go to:

```
http://localhost:8000
```

---

## Features to Demo

### 1. Text Chat

- Type a message in the input box
- Click Send or press Enter
- Watch the AI respond in real-time

### 2. Voice Chat

- Click the microphone button
- Speak your message
- The AI will respond with voice

### 3. Quick Prompts

- Click the preset prompts at the bottom
- Great for starting conversations

### 4. Settings

- Click the gear icon in the top right
- Change voice, toggle TTS, enter API key

### 5. Dark Mode

- Click the moon/sun icon
- Toggle between light and dark themes

---

## Troubleshooting

### "No Gemini API key available"

**Solution:** Make sure you set the environment variable before running the server.

### Microphone not working

**Solutions:**

1. Use Chrome browser (best support)
2. Allow microphone access when prompted
3. Check if another app is using the mic

### Voice not speaking

**Solutions:**

1. Check Settings → Voice Responses is ON
2. Try a different voice from the dropdown
3. Unmute your speakers

### Server not starting

**Solutions:**

1. Make sure you're in the `backend` folder
2. Verify all requirements are installed: `pip install -r requirements.txt`
3. Check if port 8000 is available

### WebSocket connection failed

**Solution:** The app will automatically fall back to REST API. Functionality is not affected.

---

## For Viva/Demo

### Key Points to Highlight

1. **Real-time AI** - Responses stream token-by-token via WebSocket
2. **Free AI** - Uses Google Gemini's generous free tier
3. **Voice Interaction** - Full voice input/output using browser APIs
4. **Modern UI** - Glassmorphism design, animations, responsive
5. **Fallback System** - Works even if AI is unavailable
6. **Production Ready** - Rate limiting, caching, error handling

### Demo Script

1. Show the landing page and explain the UI
2. Send a text message, show streaming response
3. Use voice input to send a message
4. Show the settings panel
5. Toggle dark mode
6. Explain the architecture (show README diagram)
7. Show the API endpoints (/api/health/, /api/metrics/)

---

## Contact

For issues or questions, please refer to the main README.md or contact the project maintainer.
