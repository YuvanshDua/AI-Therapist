from django.contrib import admin

from api.models import Message, TherapySession


@admin.register(TherapySession)
class TherapySessionAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at", "updated_at", "ended_at")
    list_filter = ("status", "created_at")
    search_fields = ("id",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "session__id")
