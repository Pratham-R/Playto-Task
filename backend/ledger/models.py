import uuid

from django.db import models
from django.utils import timezone

from .managers import MerchantManager


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    objects = MerchantManager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.PROTECT, related_name="bank_accounts"
    )
    account_holder_name = models.CharField(max_length=255)
    account_number_last4 = models.CharField(max_length=4)
    ifsc = models.CharField(max_length=11)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        indexes = [models.Index(fields=["merchant"], name="ledger_ba_merchant_idx")]

    def __str__(self):
        return f"{self.account_holder_name} ****{self.account_number_last4}"


class LedgerEntry(models.Model):
    class Kind(models.TextChoices):
        CREDIT = "CREDIT", "Credit"
        HOLD = "HOLD", "Hold"
        RELEASE = "RELEASE", "Release"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount_paise = models.BigIntegerField()
    payout = models.ForeignKey(
        "payouts.PayoutRequest",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["merchant", "-created_at"], name="ledger_entry_merchant_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_paise__gt=0),
                name="ledger_amount_positive",
            )
        ]

    def __str__(self):
        return f"{self.kind} {self.amount_paise}p — {self.merchant_id}"
