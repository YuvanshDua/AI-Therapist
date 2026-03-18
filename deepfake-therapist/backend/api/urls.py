"""API URL configuration for voice therapist MVP."""

from django.urls import path

from api import views

app_name = "api"

urlpatterns = [
    path("health/", views.HealthCheckView.as_view(), name="health"),
    path("session/start/", views.StartSessionView.as_view(), name="session-start"),
    path("session/end/", views.EndSessionView.as_view(), name="session-end"),
    path("session/<uuid:session_id>/", views.SessionDetailView.as_view(), name="session-detail"),
    path("transcribe/", views.TranscribeView.as_view(), name="transcribe"),
    path("respond/", views.RespondView.as_view(), name="respond"),
    path("tts/", views.TTSView.as_view(), name="tts"),
]
