from django.contrib import admin

from .models import IdempotencyKey, PayoutRequest


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "merchant", "amount_paise", "status", "attempts", "created_at"]
    list_filter = ["status", "merchant"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ["key", "merchant", "response_status_code", "expires_at", "created_at"]
    list_filter = ["merchant"]
