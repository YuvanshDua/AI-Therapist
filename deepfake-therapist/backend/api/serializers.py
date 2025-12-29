"""
API Serializers

DRF serializers for request/response validation.
"""

from rest_framework import serializers


class DialogueRequestSerializer(serializers.Serializer):
    """Serializer for dialogue request."""
    text = serializers.CharField(
        max_length=2000,
        required=True,
        help_text="User's message to the therapist"
    )
    api_key = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Optional OpenAI API key"
    )


class DialogueResponseSerializer(serializers.Serializer):
    """Serializer for dialogue response."""
    response = serializers.CharField(help_text="AI therapist response")
    source = serializers.CharField(help_text="Response source: openai, fallback, or cache")
    latency_ms = serializers.IntegerField(help_text="Response latency in milliseconds")


class MetricsSerializer(serializers.Serializer):
    """Serializer for metrics response."""
    total_requests = serializers.IntegerField()
    gemini_requests = serializers.IntegerField()
    local_requests = serializers.IntegerField()
    fallback_requests = serializers.IntegerField()
    rate_limited_requests = serializers.IntegerField()
    latency_median_ms = serializers.IntegerField()
    latency_p95_ms = serializers.IntegerField()
