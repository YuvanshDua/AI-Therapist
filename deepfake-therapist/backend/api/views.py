"""REST API endpoints for voice-based therapy sessions."""

from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import TherapySession
from api.serializers import (
    EndSessionSerializer,
    RespondSerializer,
    StartSessionSerializer,
    TTSRequestSerializer,
    TherapySessionSerializer,
    TranscribeSerializer,
)
from api.services.events import emit_session_event
from api.services.memory_service import MemoryService
from api.services.ollama_service import OllamaService, OllamaServiceError
from api.services.safety_service import SafetyService
from api.services.session_service import SessionService
from api.services.transcription_service import TranscriptionError, TranscriptionService
from api.services.tts_service import TTSGenerationError, TTSService

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Basic health check for the local app."""

    def get(self, _request):
        return Response(
            {
                "status": "healthy",
                "service": "Voice Therapist Backend",
                "version": "2.0.0",
            }
        )


class StartSessionView(APIView):
    """Create a new therapy session."""

    parser_classes = [JSONParser, FormParser]

    def post(self, request):
        serializer = StartSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        metadata = serializer.validated_data.get("metadata", {})
        session = SessionService.start_session(metadata=metadata)
        SessionService.add_message(
            session=session,
            role="system",
            content=(
                "Session started. The assistant should stay supportive, concise, and avoid diagnosis."
            ),
        )

        return Response(
            {
                "session_id": str(session.id),
                "status": session.status,
                "created_at": session.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class EndSessionView(APIView):
    """Mark a therapy session as ended."""

    parser_classes = [JSONParser, FormParser]

    def post(self, request):
        serializer = EndSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = get_object_or_404(TherapySession, id=serializer.validated_data["session_id"])
        SessionService.end_session(session)
        emit_session_event(str(session.id), "session_ended", {"status": session.status})

        return Response(
            {
                "session_id": str(session.id),
                "status": session.status,
                "ended_at": session.ended_at,
            }
        )


class SessionDetailView(APIView):
    """Get session metadata + transcript history."""

    def get(self, _request, session_id):
        session = get_object_or_404(TherapySession.objects.prefetch_related("messages"), id=session_id)
        payload = TherapySessionSerializer(session).data
        return Response(payload)


class TranscribeView(APIView):
    """Transcribe an uploaded user audio utterance."""

    parser_classes = [MultiPartParser, FormParser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transcription_service = TranscriptionService()

    def post(self, request):
        serializer = TranscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = get_object_or_404(TherapySession, id=serializer.validated_data["session_id"])
        if session.status != TherapySession.SessionStatus.ACTIVE:
            return Response({"error": "Session is not active"}, status=status.HTTP_400_BAD_REQUEST)

        emit_session_event(str(session.id), "listening", {"status": "transcribing"})
        audio_file = serializer.validated_data["audio"]

        try:
            result = self.transcription_service.transcribe(audio_file)
        except TranscriptionError as exc:
            logger.warning("Transcription failed: %s", exc)
            emit_session_event(str(session.id), "error", {"stage": "transcribe", "detail": str(exc)})
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        emit_session_event(str(session.id), "transcript_ready", {"transcript": result.text})
        return Response({"transcript": result.text, "source": result.source})


class RespondView(APIView):
    """Generate therapist response from transcribed user text."""

    parser_classes = [JSONParser, FormParser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.safety = SafetyService()
        self.memory = MemoryService()
        self.ollama = OllamaService()

    def post(self, request):
        serializer = RespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = get_object_or_404(TherapySession, id=serializer.validated_data["session_id"])
        if session.status != TherapySession.SessionStatus.ACTIVE:
            return Response({"error": "Session is not active"}, status=status.HTTP_400_BAD_REQUEST)

        transcript = serializer.validated_data["transcript"].strip()
        if not transcript:
            return Response({"error": "Transcript is required"}, status=status.HTTP_400_BAD_REQUEST)

        SessionService.add_message(session, role="user", content=transcript)
        emit_session_event(str(session.id), "thinking", {"status": "generating"})

        safety_result = self.safety.evaluate_user_message(transcript)
        if safety_result.crisis_detected:
            assistant_reply = safety_result.override_response
            source = "safety_override"
        else:
            rolling_summary, recent_messages = self.memory.build_context(session)
            try:
                assistant_reply = self.ollama.generate_reply(
                    latest_user_text=transcript,
                    rolling_summary=rolling_summary,
                    recent_messages=recent_messages,
                )
                source = "ollama"
            except OllamaServiceError as exc:
                logger.warning("Ollama generation failed, using fallback: %s", exc)
                assistant_reply = (
                    "I hear this feels heavy right now. I'm here with you, and we can take it one step at a time. "
                    "Would a short grounding exercise help in this moment?"
                )
                source = "fallback"

        assistant_reply = self.safety.sanitize_assistant_response(assistant_reply)
        SessionService.add_message(
            session,
            role="assistant",
            content=assistant_reply,
            metadata={"source": source, "safety_override": safety_result.crisis_detected},
        )

        summary_updated = self.memory.maybe_update_summary(
            session,
            summarizer=self.ollama.summarize_context,
        )

        emit_session_event(
            str(session.id),
            "response_ready",
            {
                "response": assistant_reply,
                "source": source,
                "summary_updated": summary_updated,
            },
        )

        return Response(
            {
                "assistant_text": assistant_reply,
                "source": source,
                "safety_override": safety_result.crisis_detected,
                "summary_updated": summary_updated,
            }
        )


class TTSView(APIView):
    """Generate local speech audio for assistant text."""

    parser_classes = [JSONParser, FormParser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tts = TTSService()

    def post(self, request):
        serializer = TTSRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        session_id = str(serializer.validated_data.get("session_id", ""))

        try:
            result = self.tts.synthesize(text=text, session_id=session_id)
        except TTSGenerationError as exc:
            logger.warning("TTS generation failed: %s", exc)
            if session_id:
                emit_session_event(session_id, "error", {"stage": "tts", "detail": str(exc)})
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if session_id:
            emit_session_event(session_id, "speaking", {"audio_url": result.audio_url})

        return Response(
            {
                "audio_url": request.build_absolute_uri(result.audio_url),
                "audio_path": result.audio_url,
                "format": result.format,
                "source": result.source,
            }
        )
