from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_endpoint_returns_ok(self):
        url = reverse("api:health")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "healthy")


class DialogueTests(TestCase):
    @patch("api.views.get_llm_response")
    def test_dialogue_uses_llm_and_tracks_latency(self, mock_llm):
        mock_llm.return_value = ("hi there", "gemini")
        url = reverse("api:dialogue")
        resp = self.client.post(
            url,
            data={"text": "hello"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["response"], "hi there")
        self.assertEqual(body["source"], "gemini")
        self.assertIn("latency_ms", body)
        self.assertIn("session_id", body)
        mock_llm.assert_called_once()

    def test_session_history_endpoint_returns_empty_for_unknown(self):
        url = reverse("api:session-history", kwargs={"session_id": "missing"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("history"), [])


class Audio2FaceTests(TestCase):
    @override_settings(A2F_OUTPUT_DIR=str(Path(__file__).parent / "missing_a2f_runs"))
    def test_a2f_latest_returns_404_when_empty(self):
        url = reverse("api:a2f-latest")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.json())
