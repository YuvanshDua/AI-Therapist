"""DRF serializers for voice therapist APIs."""

from rest_framework import serializers

from api.models import Message, TherapySession


class MessageSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "role", "content", "metadata", "timestamp"]


class TherapySessionSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = TherapySession
        fields = [
            "id",
            "status",
            "rolling_summary",
            "metadata",
            "created_at",
            "updated_at",
            "ended_at",
            "messages",
        ]


class StartSessionSerializer(serializers.Serializer):
    metadata = serializers.JSONField(required=False)


class EndSessionSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()


class TranscribeSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    audio = serializers.FileField()


class RespondSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    transcript = serializers.CharField(max_length=5000)


class TTSRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000)
    session_id = serializers.UUIDField(required=False)
