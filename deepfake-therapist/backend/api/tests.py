from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from api.models import Message, TherapySession


class HealthCheckTests(TestCase):
    def test_health_endpoint(self):
        resp = self.client.get(reverse("api:health"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "healthy")


class SessionLifecycleTests(TestCase):
    def test_start_and_get_session(self):
        start = self.client.post(
            reverse("api:session-start"),
            data={"metadata": {"client": "test"}},
            content_type="application/json",
        )
        self.assertEqual(start.status_code, 201)
        session_id = start.json()["session_id"]

        detail = self.client.get(reverse("api:session-detail", kwargs={"session_id": session_id}))
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()
        self.assertEqual(payload["status"], "active")
        self.assertGreaterEqual(len(payload["messages"]), 1)

    def test_end_session(self):
        session = TherapySession.objects.create()
        resp = self.client.post(
            reverse("api:session-end"),
            data={"session_id": str(session.id)},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        session.refresh_from_db()
        self.assertEqual(session.status, TherapySession.SessionStatus.ENDED)


class VoicePipelineTests(TestCase):
    def setUp(self):
        self.session = TherapySession.objects.create()

    @patch("api.views.TranscriptionService.transcribe")
    def test_transcribe_endpoint_success(self, mock_transcribe):
        mock_transcribe.return_value.text = "I feel overwhelmed"
        mock_transcribe.return_value.source = "faster_whisper"

        response = self.client.post(
            reverse("api:transcribe"),
            data={
                "session_id": str(self.session.id),
                "audio": self._dummy_audio_file(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transcript"], "I feel overwhelmed")

    @patch("api.views.OllamaService.generate_reply")
    @patch("api.views.OllamaService.summarize_context")
    def test_respond_endpoint_creates_messages(self, _mock_summary, mock_reply):
        mock_reply.return_value = "That sounds really hard. What feels most intense right now?"

        response = self.client.post(
            reverse("api:respond"),
            data={
                "session_id": str(self.session.id),
                "transcript": "I'm anxious about tomorrow",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "ollama")
        self.assertEqual(Message.objects.filter(session=self.session, role="user").count(), 1)
        self.assertEqual(Message.objects.filter(session=self.session, role="assistant").count(), 1)

    @patch("api.views.OllamaService.generate_reply")
    def test_respond_crisis_message_uses_safety_override(self, mock_reply):
        response = self.client.post(
            reverse("api:respond"),
            data={
                "session_id": str(self.session.id),
                "transcript": "I want to kill myself",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "safety_override")
        self.assertTrue(response.json()["safety_override"])
        mock_reply.assert_not_called()

    @patch("api.views.TTSService.synthesize")
    def test_tts_endpoint_success(self, mock_tts):
        mock_tts.return_value.audio_url = "/media/tts/test.wav"
        mock_tts.return_value.source = "piper"
        mock_tts.return_value.format = "wav"

        response = self.client.post(
            reverse("api:tts"),
            data={"session_id": str(self.session.id), "text": "Take a slow breath."},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("audio_url", payload)
        self.assertEqual(payload["source"], "piper")

    def _dummy_audio_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile("sample.wav", b"RIFF....WAVEfmt ", content_type="audio/wav")
