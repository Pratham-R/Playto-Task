import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


def _idem_expires():
    return timezone.now() + timedelta(hours=24)


class PayoutRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        "ledger.Merchant", on_delete=models.PROTECT, related_name="payouts"
    )
    bank_account = models.ForeignKey(
        "ledger.BankAccount", on_delete=models.PROTECT, related_name="payouts"
    )
    amount_paise = models.BigIntegerField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    processing_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # worker scans for pending/processing payouts
            models.Index(fields=["status", "processing_started_at"], name="payouts_status_proc_idx"),
            # dashboard history table
            models.Index(fields=["merchant", "-created_at"], name="payouts_merchant_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_paise__gt=0),
                name="payout_amount_positive",
            )
        ]

    def __str__(self):
        return f"Payout {self.id} — {self.status} — {self.amount_paise}p"


class IdempotencyKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        "ledger.Merchant", on_delete=models.CASCADE, related_name="idempotency_keys"
    )
    # UUID string supplied by client in Idempotency-Key header
    key = models.CharField(max_length=36)
    # SHA-256 of canonical request body — mismatch = 409 Conflict
    request_fingerprint = models.CharField(max_length=64)
    # null while the first request is still in flight
    response_status_code = models.SmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    payout = models.OneToOneField(
        PayoutRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="idempotency_key",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField(default=_idem_expires)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "key"], name="uniq_idem_per_merchant"
            )
        ]
        indexes = [
            models.Index(fields=["expires_at"], name="payouts_idem_expires_idx"),
        ]

    def __str__(self):
        return f"IdempKey {self.key} — {self.merchant_id}"
