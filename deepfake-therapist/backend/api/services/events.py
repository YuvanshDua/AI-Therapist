"""WebSocket event helpers for session updates."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def emit_session_event(session_id: str, event: str, payload: dict | None = None) -> None:
    """Broadcast a session-scoped event to websocket subscribers."""
    layer = get_channel_layer()
    if not layer or not session_id:
        return

    async_to_sync(layer.group_send)(
        f"session_{session_id}",
        {
            "type": "session.event",
            "event": event,
            "payload": payload or {},
        },
    )
