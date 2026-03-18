"""WebSocket consumer for per-session live call events."""

from __future__ import annotations

import json

from channels.generic.websocket import AsyncWebsocketConsumer


class SessionConsumer(AsyncWebsocketConsumer):
    """Pushes session lifecycle events (thinking/speaking/transcript/etc.) to clients."""

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = f"session_{self.session_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "event": "connected",
                    "payload": {"session_id": self.session_id},
                }
            )
        )


class LegacyStreamConsumer(AsyncWebsocketConsumer):
    """
    Backward-compatible endpoint for older frontend clients that still connect
    to /ws/stream/. Keeps connection stable and nudges users to the new flow.
    """

    async def connect(self):
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connected",
                    "message": "Legacy stream endpoint is deprecated. Use the call UI at '/'.",
                }
            )
        )

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            return
        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "message": "This endpoint is deprecated. Start a session via the new call UI.",
                }
            )
        )

    async def disconnect(self, _close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Optional client->server messaging hook; kept minimal for MVP.
        if bytes_data:
            return
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            data = {"event": "invalid_json"}

        if data.get("event") == "ping":
            await self.send(text_data=json.dumps({"event": "pong", "payload": {}}))

    async def session_event(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "event": event.get("event", "unknown"),
                    "payload": event.get("payload", {}),
                }
            )
        )
