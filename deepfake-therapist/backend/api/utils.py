"""
Utility Functions

Contains rate limiter, caching, Gemini proxy, and fallback responder.
"""

import os
import time
import random
import logging
import json
from typing import Tuple, Optional
from collections import deque
from threading import Lock
from django.conf import settings
import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """
    Simple in-memory rate limiter.
    Limits requests per client IP per minute.
    """
    
    def __init__(self, calls_per_minute: int = 10):
        self.calls_per_minute = calls_per_minute
        self.clients = {}  # {ip: deque of timestamps}
        self.lock = Lock()
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if client is allowed to make a request."""
        with self.lock:
            now = time.time()
            window_start = now - 60  # 1 minute window
            
            if client_ip not in self.clients:
                self.clients[client_ip] = deque()
            
            # Remove old timestamps
            while self.clients[client_ip] and self.clients[client_ip][0] < window_start:
                self.clients[client_ip].popleft()
            
            # Check if under limit
            if len(self.clients[client_ip]) < self.calls_per_minute:
                self.clients[client_ip].append(now)
                return True
            
            return False


# Global rate limiter instance
rate_limiter = RateLimiter(
    calls_per_minute=getattr(settings, 'RATE_LIMIT_CALLS_PER_MINUTE', 10)
)


# =============================================================================
# Metrics Tracker
# =============================================================================

class MetricsTracker:
    """
    Tracks API usage metrics.
    """
    
    def __init__(self):
        self.lock = Lock()
        self.total_requests = 0
        self.gemini_requests = 0
        self.local_requests = 0
        self.fallback_requests = 0
        self.rate_limited_requests = 0
        self.latencies = deque(maxlen=1000)  # Keep last 1000 latencies
    
    def record_request(self, latency_ms: int, source: str):
        """Record a completed request."""
        with self.lock:
            self.total_requests += 1
            self.latencies.append(latency_ms)
            
            if source.startswith('gemini'):
                self.gemini_requests += 1
            elif source.startswith('local'):
                self.local_requests += 1
            else:
                self.fallback_requests += 1
    
    def record_rate_limit(self):
        """Record a rate-limited request."""
        with self.lock:
            self.rate_limited_requests += 1
    
    def get_metrics(self) -> dict:
        """Get current metrics."""
        with self.lock:
            latencies = list(self.latencies)
            
            if latencies:
                sorted_latencies = sorted(latencies)
                median = sorted_latencies[len(sorted_latencies) // 2]
                p95_idx = int(len(sorted_latencies) * 0.95)
                p95 = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
            else:
                median = 0
                p95 = 0
            
            return {
                'total_requests': self.total_requests,
                'gemini_requests': self.gemini_requests,
                'local_requests': self.local_requests,
                'fallback_requests': self.fallback_requests,
                'rate_limited_requests': self.rate_limited_requests,
                'latency_median_ms': median,
                'latency_p95_ms': p95,
            }


# Global metrics tracker instance
metrics_tracker = MetricsTracker()


# =============================================================================
# Response Cache
# =============================================================================

class ResponseCache:
    """
    Simple in-memory response cache.
    Caches recent prompt/response pairs to reduce API calls.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # {prompt_hash: (response, timestamp)}
        self.lock = Lock()
    
    def _make_key(self, prompt: str, provider: str) -> int:
        provider_prefix = provider.lower().strip() if provider else 'default'
        return hash(f"{provider_prefix}:{prompt.lower().strip()}")

    def get(self, prompt: str, provider: str = '') -> Optional[str]:
        """Get cached response for prompt."""
        key = self._make_key(prompt, provider)
        with self.lock:
            if key in self.cache:
                response, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    logger.debug(f"Cache hit for prompt")
                    return response
                else:
                    del self.cache[key]
        return None
    
    def set(self, prompt: str, response: str, provider: str = ''):
        """Cache a response for a prompt."""
        key = self._make_key(prompt, provider)
        with self.lock:
            # Evict old entries if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]
            
            self.cache[key] = (response, time.time())


# Global cache instance
response_cache = ResponseCache()


# =============================================================================
# Google Gemini Integration (NEW SDK)
# =============================================================================

# Therapist system prompt
THERAPIST_SYSTEM_PROMPT = """You are a calm, licensed therapist. Speak as a human therapist would:
- Lead with reflective listening: name the feeling, validate, and show you heard the meaning.
- Ask gentle, open questions to help the client explore.
- Offer grounded coping strategies when appropriate (breathing, reframing, journaling, boundaries).
- Keep boundaries: you can diagnose, you can replace professional care, and you defer emergencies to real help.
- be brutally honest and direct with the client. Always act like you are the best therapist in the world
- Tone: warm, steady, concise (2–3 short sentences), conversational, first person, no mention of being an AI."""


def normalize_provider(provider: str) -> str:
    provider_normalized = (provider or getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini')).lower()
    if provider_normalized not in ('gemini', 'local'):
        return 'gemini'
    return provider_normalized


def get_llm_response(user_text: str, provider: str = '', user_api_key: str = '') -> Tuple[str, str]:
    """
    Get response from the configured LLM (Gemini or local).
    """
    provider = normalize_provider(provider)

    cached = response_cache.get(user_text, provider)
    if cached:
        logger.info("Cache hit, returning cached response")
        return cached, f"{provider}-cache"

    if provider == 'local':
        response_text = get_local_response(user_text)
        source = 'local'
    else:
        response_text, source = get_gemini_response(user_text, user_api_key)

    response_cache.set(user_text, response_text, provider)
    return response_text, source


def get_gemini_response(user_text: str, user_api_key: str = '') -> Tuple[str, str]:
    """
    Get response from Google Gemini API using the NEW SDK.
    
    Args:
        user_text: User's message
        user_api_key: Optional user-provided API key
    
    Returns:
        Tuple of (response_text, source)
    
    Raises:
        Exception if Gemini is unavailable
    """
    # Get API key (user-provided or from environment)
    api_key = user_api_key or getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    
    logger.info(f"API key available: {bool(api_key)}, length: {len(api_key) if api_key else 0}")
    
    if not api_key:
        logger.warning("No Gemini API key available, using fallback")
        raise Exception("No Gemini API key configured")
    
    try:
        from google import genai
        
        logger.info("Creating Gemini client...")
        
        # Create client with API key
        client = genai.Client(api_key=api_key)
        
        # Get model name from settings
        model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
        logger.info(f"Using model: {model_name}")
        
        # Create the full prompt with system instruction
        full_prompt = f"{THERAPIST_SYSTEM_PROMPT}\n\nUser: {user_text}\n\nTherapist:"
        
        # Generate response
        logger.info("Generating response...")
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt
        )
        
        response_text = response.text.strip()
        logger.info(f"Got response: {response_text[:50]}...")
        
        return response_text, 'gemini'
        
    except ImportError as e:
        logger.error(f"Google GenAI library not installed: {e}")
        raise Exception("Google GenAI library not available. Run: pip install google-genai")
    except Exception as e:
        logger.error(f"Gemini API error: {type(e).__name__}: {e}")
        raise


def get_gemini_streaming_response(user_text: str, api_key: str = ''):
    """
    Get streaming response from Gemini API.
    Yields chunks of text as they're generated.
    
    Args:
        user_text: User's message
        api_key: Gemini API key
    
    Yields:
        Text chunks
    """
    from google import genai
    
    logger.info(f"Streaming: API key available: {bool(api_key)}")
    
    # Create client with API key
    client = genai.Client(api_key=api_key)
    
    # Get model name
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
    
    # Create the full prompt with system instruction
    full_prompt = f"{THERAPIST_SYSTEM_PROMPT}\n\nUser: {user_text}\n\nTherapist:"
    
    # Generate streaming response
    logger.info("Starting streaming response...")
    response = client.models.generate_content_stream(
        model=model_name,
        contents=full_prompt
    )
    
    for chunk in response:
        if chunk.text:
            yield chunk.text


def get_local_response(user_text: str) -> str:
    """
    Get response from a local LLM server (e.g., Ollama /api/chat).
    """
    base_url = getattr(settings, 'LOCAL_LLM_URL', 'http://localhost:11434').rstrip('/')
    model = getattr(settings, 'LOCAL_LLM_MODEL', 'llama3.1:8b-instruct-q4_0')
    num_predict = getattr(settings, 'LOCAL_NUM_PREDICT', 256)
    temperature = getattr(settings, 'LOCAL_TEMPERATURE', 0.6)
    url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": THERAPIST_SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
        "options": {
            "num_predict": num_predict,
            "temperature": temperature,
        },
    }

    try:
        with httpx.Client(timeout=45) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            message = data.get("message", {}).get("content") or data.get("response") or data.get("text") or ''
            if not message:
                raise ValueError("Local model returned empty response")
            return message.strip()
    except Exception as e:
        logger.error(f"Local LLM error: {type(e).__name__}: {e}")
        raise


def get_local_streaming_response(user_text: str):
    """
    Stream response from a local LLM server that supports streamed chat (Ollama-compatible).
    """
    base_url = getattr(settings, 'LOCAL_LLM_URL', 'http://localhost:11434').rstrip('/')
    model = getattr(settings, 'LOCAL_LLM_MODEL', 'llama3.1:8b-instruct-q4_0')
    num_predict = getattr(settings, 'LOCAL_NUM_PREDICT', 256)
    temperature = getattr(settings, 'LOCAL_TEMPERATURE', 0.6)
    url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": THERAPIST_SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "stream": True,
        "options": {
            "num_predict": num_predict,
            "temperature": temperature,
        },
    }

    with httpx.Client(timeout=None) as client:
        with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Ollama streams messages as {"message": {"content": "..."}}
                    if data.get('done'):
                        break
                    token = data.get('message', {}).get('content') or data.get('response') or ''
                    if token:
                        yield token
                except json.JSONDecodeError:
                    logger.debug("Skipping non-JSON streaming line from local LLM")


def get_llm_streaming_response(user_text: str, provider: str = '', api_key: str = ''):
    """
    Stream response from the configured LLM.
    """
    provider = normalize_provider(provider)
    if provider == 'local':
        yield from get_local_streaming_response(user_text)
    else:
        yield from get_gemini_streaming_response(user_text, api_key)


# =============================================================================
# Fallback Template Responder
# =============================================================================

# Empathetic response templates for when AI is unavailable
FALLBACK_RESPONSES = [
    "I hear you, and I appreciate you sharing that with me. It sounds like you're going through something important. Would you like to tell me more about how that makes you feel?",
    "Thank you for opening up. What you're experiencing sounds meaningful. Can you help me understand a bit more about what's on your mind?",
    "I'm here to listen. It takes courage to express yourself like this. What feels most important for you to explore right now?",
    "That sounds like it weighs on you. I want you to know that your feelings are valid. What would feel most helpful to discuss?",
    "I appreciate your trust in sharing this with me. Sometimes talking through our thoughts can help us see things more clearly. What else is coming up for you?",
    "It sounds like there's a lot going on for you. Take your time - I'm here to listen without judgment. What feels most pressing?",
]

GREETING_RESPONSES = [
    "Hello! I'm glad you're here. I'm here to listen and support you. What's on your mind today?",
    "Hi there! Thank you for reaching out. This is a safe space to share whatever you'd like. How are you feeling?",
    "Welcome! I'm here to listen. Whatever you're experiencing, you don't have to face it alone. What would you like to talk about?",
]

ACKNOWLEDGMENT_RESPONSES = [
    "I understand. Please, continue whenever you're ready.",
    "I see. Take your time - there's no rush here.",
    "Okay, I'm following you. What comes to mind next?",
]


def get_fallback_response(user_text: str) -> str:
    """
    Get a template-based empathetic response.
    Used when Gemini is unavailable.
    
    Args:
        user_text: User's message
    
    Returns:
        Empathetic response string
    """
    user_lower = user_text.lower().strip()
    
    # Check for greetings
    greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
    if any(g in user_lower for g in greetings):
        return random.choice(GREETING_RESPONSES)
    
    # Check for short acknowledgments
    if len(user_text.split()) <= 3:
        return random.choice(ACKNOWLEDGMENT_RESPONSES)
    
    # Return a general empathetic response
    return random.choice(FALLBACK_RESPONSES)
