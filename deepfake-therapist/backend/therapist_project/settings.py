"""
Django settings for therapist_project.

AI Therapist Avatar - Production-ready configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Application definition
INSTALLED_APPS = [
    'daphne',  # ASGI server for WebSocket support
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework',
    'corsheaders',
    'channels',
    # Local apps
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'therapist_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ASGI configuration for WebSocket support
ASGI_APPLICATION = 'therapist_project.asgi.application'

# Channel layers configuration (Redis in production if configured)
REDIS_URL = os.environ.get('CHANNEL_REDIS_URL', '')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

WSGI_APPLICATION = 'therapist_project.wsgi.application'

# Database - using SQLite for simplicity (no data persistence needed)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR.parent / 'frontend',  # Serve frontend files
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# CORS Configuration (for local development)
# =============================================================================
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only allow all in development
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:3000',  # If using separate frontend dev server
]

# =============================================================================
# REST Framework Configuration
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

# =============================================================================
# Google Gemini Configuration
# =============================================================================
# Get your FREE API key from: https://aistudio.google.com/app/apikey
# Free tier: 15 RPM, 1 million tokens/day for Gemini Flash
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')

# =============================================================================
# Local LLM Configuration
# =============================================================================
# Switch between providers with LLM_PROVIDER (gemini|local)
DEFAULT_LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'gemini').lower()
LOCAL_LLM_URL = os.environ.get('LOCAL_LLM_URL', 'http://localhost:11434')
LOCAL_LLM_MODEL = os.environ.get('LOCAL_LLM_MODEL', 'ALIENTELLIGENCE/mindwell')
LOCAL_NUM_PREDICT = int(os.environ.get('LOCAL_NUM_PREDICT', '256'))
LOCAL_TEMPERATURE = float(os.environ.get('LOCAL_TEMPERATURE', '0.6'))

# =============================================================================
# Rate Limiting Configuration
# =============================================================================
RATE_LIMIT_CALLS_PER_MINUTE = int(os.environ.get('RATE_LIMIT_CALLS_PER_MINUTE', '10'))

# =============================================================================
# Audio2Face (A2F) Output Configuration
# =============================================================================
A2F_OUTPUT_DIR = os.environ.get(
    'A2F_OUTPUT_DIR',
    str(BASE_DIR.parent.parent / 'Audio2Face-3D-Samples' / 'scripts' / 'audio2face_3d_api_client')
)
A2F_CONFIG_PATH = os.environ.get('A2F_CONFIG_PATH', str(Path(A2F_OUTPUT_DIR) / 'config' / 'config_claire.yml'))
A2F_API_KEY = os.environ.get('A2F_API_KEY', '')
A2F_FUNCTION_ID = os.environ.get('A2F_FUNCTION_ID', '')
A2F_RUN_TIMEOUT = int(os.environ.get('A2F_RUN_TIMEOUT', '180'))

# =============================================================================
# Logging Configuration
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'api': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
