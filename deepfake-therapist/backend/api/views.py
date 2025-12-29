"""
REST API Views

Handles HTTP endpoints for the AI Therapist application.
"""

import logging
import time
import uuid
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    get_fallback_response,
    get_llm_response,
    metrics_tracker,
    rate_limiter,
)
from .session_store import conversation_store
from .a2f import build_a2f_payload, resolve_run_dir, resolve_audio_path
from .a2f_runner import generate_a2f_run, A2FGenerationError

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check endpoint.
    GET /api/health/ - Returns server health status.
    """
    
    def get(self, request):
        """Return health status of the server."""
        return Response({
            'status': 'healthy',
            'service': 'AI Therapist Backend',
            'version': '1.0.0',
        })


class DialogueView(APIView):
    """
    Main dialogue endpoint.
    POST /api/dialogue/ - Accept user text, return AI therapist response.
    
    Request body:
    {
        "text": "User's message",
        "api_key": "optional OpenAI API key"
    }
    
    Response:
    {
        "response": "AI therapist response",
        "source": "openai" | "fallback",
        "latency_ms": 123,
        "session_id": "uuid4..."
    }
    """
    
    def post(self, request):
        """Process user dialogue and return AI response."""
        start_time = time.time()
        
        # Extract request data
        user_text = request.data.get('text', '').strip()
        user_api_key = request.data.get('api_key', '')
        provider = request.data.get('provider', getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini'))
        session_id = request.data.get('session_id') or uuid.uuid4().hex
        
        # Validate input
        if not user_text:
            return Response(
                {'error': 'Text field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check rate limit
        client_ip = self.get_client_ip(request)
        if not rate_limiter.is_allowed(client_ip):
            metrics_tracker.record_rate_limit()
            return Response(
                {'error': 'Rate limit exceeded. Please wait before sending another message.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Try selected provider first, fallback if unavailable
        try:
            response_text, source = get_llm_response(user_text, provider, user_api_key)
        except Exception as e:
            logger.warning(f"Primary provider failed, using fallback: {e}")
            response_text = get_fallback_response(user_text)
            source = 'fallback'
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Record metrics
        metrics_tracker.record_request(latency_ms, source)

        # Persist conversation history in-memory for the session
        conversation_store.add(session_id, 'user', user_text)
        conversation_store.add(session_id, 'assistant', response_text)
        
        logger.info(f"Dialogue processed: latency={latency_ms}ms, source={source}")
        
        return Response({
            'response': response_text,
            'source': source,
            'latency_ms': latency_ms,
            'session_id': session_id,
        })
    
    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class MetricsView(APIView):
    """
    Metrics endpoint.
    GET /api/metrics/ - Returns API usage statistics.
    """
    
    def get(self, request):
        """Return API metrics."""
        return Response(metrics_tracker.get_metrics())


class SessionHistoryView(APIView):
    """
    Session history endpoint.
    GET /api/session/<session_id>/ - Returns the stored conversation turns.
    """

    def get(self, request, session_id: str):
        history = conversation_store.get(session_id)
        if not history:
            return Response({'history': []})
        return Response({'history': history})


class TTSView(APIView):
    """
    Text-to-Speech endpoint using Google Cloud TTS.
    POST /api/tts/ - Convert text to speech audio.
    
    Request body:
    {
        "text": "Text to convert to speech",
        "voice_name": "en-US-Neural2-F" (optional),
        "speaking_rate": 1.0 (optional)
    }
    
    Response: Audio file (MP3) or base64-encoded audio
    """
    
    def post(self, request):
        """Convert text to speech and return audio."""
        import base64
        import os
        
        text = request.data.get('text', '').strip()
        voice_name = request.data.get('voice_name', 'en-US-Neural2-F')  # Female neural voice
        speaking_rate = float(request.data.get('speaking_rate', 0.95))
        
        if not text:
            return Response(
                {'error': 'Text field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Limit text length for free tier (to not exhaust quota)
        if len(text) > 5000:
            text = text[:5000]
        
        try:
            from google.cloud import texttospeech
            
            # Initialize client
            # Requires GOOGLE_APPLICATION_CREDENTIALS env var pointing to service account JSON
            client = texttospeech.TextToSpeechClient()
            
            # Set the text input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name,
            )
            
            # Select the audio encoding
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=0.0,  # Natural pitch
            )
            
            # Perform the TTS request
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Return audio as base64
            audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
            
            return Response({
                'audio': audio_base64,
                'format': 'mp3',
                'source': 'google-cloud-tts'
            })
            
        except ImportError:
            logger.error("Google Cloud TTS library not installed")
            return Response(
                {'error': 'Google Cloud TTS not available. Using browser TTS.', 'use_browser_tts': True},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Google Cloud TTS error: {e}")
            return Response(
                {'error': str(e), 'use_browser_tts': True},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class A2FLatestView(APIView):
    """
    Audio2Face output endpoint.
    GET /api/a2f/latest/ - Returns parsed A2F output (latest run or by run_id).
    """

    def get(self, request):
        run_id = request.query_params.get('run_id')
        base_dir = Path(getattr(settings, 'A2F_OUTPUT_DIR', ''))
        run_dir = resolve_run_dir(base_dir, run_id)
        if not run_dir:
            return Response(
                {'error': 'No Audio2Face output found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        payload = build_a2f_payload(run_dir)
        return Response(payload)


class A2FAudioView(APIView):
    """
    Audio2Face audio endpoint.
    GET /api/a2f/audio/<run_id>/ - Streams the generated audio file.
    """

    def get(self, request, run_id: str):
        base_dir = Path(getattr(settings, 'A2F_OUTPUT_DIR', ''))
        run_dir = resolve_run_dir(base_dir, run_id)
        if not run_dir:
            raise Http404("Audio2Face run not found")
        audio_path = resolve_audio_path(run_dir)
        if not audio_path:
            raise Http404("Audio file not found")
        return FileResponse(open(audio_path, 'rb'), content_type='audio/wav')


class A2FGenerateView(APIView):
    """
    Kick off a new Audio2Face generation from text using Google TTS + NVIDIA NIM client.
    POST /api/a2f/generate/
    """

    def post(self, request):
        text = request.data.get('text', '').strip()
        voice_name = request.data.get('voice_name', 'en-US-Neural2-F')
        speaking_rate = float(request.data.get('speaking_rate', 0.95))
        a2f_api_key = request.data.get('a2f_api_key', '')
        function_id = request.data.get('function_id', '')

        if not text:
            return Response({'error': 'Text field is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            run_dir = generate_a2f_run(
                text,
                voice_name=voice_name,
                speaking_rate=speaking_rate,
                api_key=a2f_api_key,
                function_id=function_id,
            )
            payload = build_a2f_payload(run_dir)
            return Response(payload, status=status.HTTP_201_CREATED)
        except A2FGenerationError as e:
            logger.error("A2F generation failed: %s", e)
            return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error("Unexpected A2F generation error: %s", e)
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
