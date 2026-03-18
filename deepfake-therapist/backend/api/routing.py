"""WebSocket routes for session-scoped call updates."""

from django.urls import re_path

from api import consumers

websocket_urlpatterns = [
    re_path(r"ws/stream/$", consumers.LegacyStreamConsumer.as_asgi()),
    re_path(r"ws/session/(?P<session_id>[0-9a-f-]+)/$", consumers.SessionConsumer.as_asgi()),
]
