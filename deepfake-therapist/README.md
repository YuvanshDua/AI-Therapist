# MindfulAI - AI Therapist Avatar

<div align="center">

![MindfulAI Logo](https://img.shields.io/badge/MindfulAI-AI%20Therapist-667eea?style=for-the-badge&logo=brain&logoColor=white)

**A Real-time AI-Powered Mental Wellness Companion**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.x-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-AI-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Configuration](#-configuration)
- [Screenshots](#-screenshots)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**MindfulAI** is a production-quality web application that provides an AI-powered mental wellness companion. It combines cutting-edge AI technology with an intuitive, calming user interface to create a supportive space for users to express their thoughts and feelings.

### Problem Statement

Mental health support is often inaccessible due to cost, stigma, or availability. MindfulAI provides an always-available, non-judgmental AI companion that can offer initial support and coping strategies.

### Solution

A real-time conversational AI therapist with:

- **Voice interaction** using Web Speech API
- **AI responses** powered by Google Gemini
- **Animated avatar** for human-like engagement
- **Professional UI** designed for mental wellness

---

## ✨ Features

### Core Features

| Feature                | Description                               |
| ---------------------- | ----------------------------------------- |
| 🎙️ **Voice Chat**      | Speak naturally using Speech-to-Text      |
| 🤖 **AI Responses**    | Empathetic responses via Google Gemini AI |
| 🔊 **Voice Output**    | Text-to-Speech for natural conversation   |
| 💬 **Chat Interface**  | Real-time streaming with message history  |
| 👤 **Animated Avatar** | Visual feedback during conversations      |

### Technical Features

| Feature                    | Description                                  |
| -------------------------- | -------------------------------------------- |
| ⚡ **WebSocket Streaming** | Real-time token-by-token response delivery   |
| 🔄 **Fallback System**     | Template-based responses when AI unavailable |
| 🛡️ **Rate Limiting**       | Protection against API abuse                 |
| 📊 **Metrics Tracking**    | API usage and latency monitoring             |
| 🌙 **Dark Mode**           | Eye-friendly dark theme support              |

### User Experience

- **Quick Prompts**: Pre-defined conversation starters
- **Voice Selection**: Choose from available TTS voices
- **Responsive Design**: Works on mobile and desktop
- **Glassmorphism UI**: Modern, calming visual design

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐ │
│  │   UI    │  │  STT    │  │  TTS    │  │    Avatar Module    │ │
│  │ (HTML/  │  │ (Web    │  │ (Web    │  │    (Animations)     │ │
│  │  CSS/JS)│  │ Speech) │  │ Speech) │  │                     │ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └─────────────────────┘ │
│       │            │            │                                │
│       └────────────┴────────────┴────────────────────────────────┤
│                              │                                   │
│              ┌───────────────┴───────────────┐                   │
│              │  WebSocket / REST API Client  │                   │
│              └───────────────┬───────────────┘                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                    ═══════════════════════
                    │ HTTP/WebSocket │
                    ═══════════════════════
                               │
┌──────────────────────────────┼───────────────────────────────────┐
│                       BACKEND (Django)                           │
├──────────────────────────────┼───────────────────────────────────┤
│              ┌───────────────┴───────────────┐                   │
│              │      Django Channels          │                   │
│              │   (ASGI + WebSocket)          │                   │
│              └───────────────┬───────────────┘                   │
│                              │                                   │
│  ┌─────────────┬─────────────┼─────────────┬─────────────────┐   │
│  │             │             │             │                 │   │
│  ▼             ▼             ▼             ▼                 │   │
│ ┌───────┐ ┌─────────┐ ┌───────────┐ ┌──────────┐            │   │
│ │Health │ │Dialogue │ │WebSocket  │ │ Metrics  │            │   │
│ │ Check │ │  View   │ │ Consumer  │ │  View    │            │   │
│ └───────┘ └────┬────┘ └─────┬─────┘ └──────────┘            │   │
│                │            │                                │   │
│                └────────┬───┘                                │   │
│                         ▼                                    │   │
│               ┌─────────────────┐                            │   │
│               │  Utils Module   │                            │   │
│               │  - Rate Limiter │                            │   │
│               │  - Cache        │                            │   │
│               │  - Gemini API   │                            │   │
│               │  - Fallback     │                            │   │
│               └────────┬────────┘                            │   │
└────────────────────────┼─────────────────────────────────────────┘
                         │
                ═════════════════
                │ HTTPS API │
                ═════════════════
                         │
                         ▼
              ┌─────────────────────┐
              │   Google Gemini AI  │
              │   (Free Tier API)   │
              └─────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend

| Technology                | Purpose                   |
| ------------------------- | ------------------------- |
| **Python 3.9+**           | Core programming language |
| **Django 4.x**            | Web framework             |
| **Django REST Framework** | REST API development      |
| **Django Channels**       | WebSocket support         |
| **Google Gemini AI**      | Large Language Model      |

### Frontend

| Technology         | Purpose               |
| ------------------ | --------------------- |
| **HTML5/CSS3/JS**  | Core web technologies |
| **Tailwind CSS**   | Utility-first styling |
| **Web Speech API** | STT and TTS           |

### Key Libraries

```
Django>=4.2.0
djangorestframework>=3.14.0
django-cors-headers>=4.3.0
channels>=4.0.0
daphne>=4.0.0
google-genai>=1.0.0
python-dotenv>=1.0.0
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Google Gemini API key (free)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/mindfulai.git
cd mindfulai
```

2. **Create virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**

```bash
cd deepfake-therapist/backend
pip install -r requirements.txt
```

4. **Get Gemini API Key**

- Visit: https://aistudio.google.com/app/apikey
- Create a free API key
- It's FREE with generous limits!

5. **Set environment variables**

```bash
# Windows
set GEMINI_API_KEY=your-api-key-here

# macOS/Linux
export GEMINI_API_KEY=your-api-key-here
```

6. **Run the server**

```bash
python manage.py runserver
```

7. **Open in browser**

```
http://localhost:8000
```

---

## 📁 Project Structure

```
deepfake-therapist/
├── backend/
│   ├── api/                    # API application
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── consumers.py        # WebSocket consumers
│   │   ├── routing.py          # WebSocket routes
│   │   ├── serializers.py      # DRF serializers
│   │   ├── urls.py             # REST API routes
│   │   ├── utils.py            # Utilities (Gemini, cache, etc.)
│   │   └── views.py            # REST views
│   │
│   ├── therapist_project/      # Django project settings
│   │   ├── __init__.py
│   │   ├── asgi.py             # ASGI config
│   │   ├── settings.py         # Project settings
│   │   ├── urls.py             # Main URL config
│   │   └── wsgi.py             # WSGI config
│   │
│   ├── templates/              # Django templates
│   │   └── index.html
│   │
│   ├── static/                 # Symlink to frontend/src
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html              # Main HTML file
│   └── src/
│       ├── script.js           # Main JavaScript
│       ├── avatar.js           # Avatar animations
│       └── therapist.png       # Avatar image
│
└── docs/
    ├── README.md
    ├── LOCAL_RUN.md
    ├── architecture_diagram.png
    └── viva_QnA.md
```

---

## 📡 API Documentation

### REST Endpoints

#### Health Check

```http
GET /api/health/
```

Response:

```json
{
  "status": "healthy",
  "service": "AI Therapist Backend",
  "version": "1.0.0"
}
```

#### Dialogue

```http
POST /api/dialogue/
Content-Type: application/json

{
    "text": "Hello, I'm feeling stressed",
    "api_key": "optional-gemini-api-key"
}
```

Response:

```json
{
  "response": "I hear you...",
  "source": "gemini",
  "latency_ms": 245
}
```

#### Metrics

```http
GET /api/metrics/
```

Response:

```json
{
  "total_requests": 100,
  "gemini_requests": 85,
  "fallback_requests": 15,
  "latency_median_ms": 200
}
```

### WebSocket

```javascript
// Connect
ws://localhost:8000/ws/stream/

// Send
{"text": "Hello", "api_key": "optional"}

// Receive
{"type": "start", "source": "gemini"}
{"type": "token", "content": "Hello "}
{"type": "token", "content": "there!"}
{"type": "done"}
```

---

## ⚙️ Configuration

### Environment Variables

| Variable                      | Description           | Default          |
| ----------------------------- | --------------------- | ---------------- |
| `GEMINI_API_KEY`              | Google Gemini API key | Required         |
| `GEMINI_MODEL`                | Model to use          | gemini-2.0-flash |
| `DEBUG`                       | Debug mode            | True             |
| `RATE_LIMIT_CALLS_PER_MINUTE` | API rate limit        | 10               |

### .env Example

```env
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash
RATE_LIMIT_CALLS_PER_MINUTE=10
```

---

## 📸 Screenshots

_Screenshots will be added during the demo presentation_

---

## 🎓 Academic Notes

This project was developed as a **10-credit BTech Major Project** demonstrating:

1. **Full-stack Development**: Django backend + JavaScript frontend
2. **AI Integration**: Google Gemini AI for natural language processing
3. **Real-time Communication**: WebSocket for streaming responses
4. **Modern UI/UX**: Glassmorphism design, animations, accessibility
5. **Software Engineering**: Clean architecture, documentation, error handling

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Google Gemini AI for the language model
- Tailwind CSS for the design system
- Django community for the excellent framework

---

<div align="center">

**Built with ❤️ for mental wellness support**

</div>
