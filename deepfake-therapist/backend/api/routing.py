"""
WebSocket URL Routing

Defines WebSocket endpoints for real-time streaming.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # WebSocket endpoint for streaming LLM tokens
    re_path(r'ws/stream/$', consumers.StreamConsumer.as_asgi()),
]
