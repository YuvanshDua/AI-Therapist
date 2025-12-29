"""
API URL Configuration

Defines REST API endpoints for the AI Therapist application.
"""

from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Health check endpoint
    path('health/', views.HealthCheckView.as_view(), name='health'),
    
    # Main dialogue endpoint - accepts user text, returns AI response
    path('dialogue/', views.DialogueView.as_view(), name='dialogue'),

    # Session history endpoint
    path('session/<str:session_id>/', views.SessionHistoryView.as_view(), name='session-history'),
    
    # Metrics endpoint - shows API usage statistics
    path('metrics/', views.MetricsView.as_view(), name='metrics'),
    
    # Text-to-Speech endpoint - converts text to audio using Google Cloud TTS
    path('tts/', views.TTSView.as_view(), name='tts'),

    # Audio2Face outputs
    path('a2f/latest/', views.A2FLatestView.as_view(), name='a2f-latest'),
    path('a2f/audio/<str:run_id>/', views.A2FAudioView.as_view(), name='a2f-audio'),
    path('a2f/generate/', views.A2FGenerateView.as_view(), name='a2f-generate'),
]
