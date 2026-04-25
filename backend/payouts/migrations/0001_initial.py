import django.db.models.deletion
import django.utils.timezone
import payouts.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("ledger", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PayoutRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payouts",
                        to="ledger.merchant",
                    ),
                ),
                (
                    "bank_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payouts",
                        to="ledger.bankaccount",
                    ),
                ),
                ("amount_paise", models.BigIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=12,
                    ),
                ),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_error", models.TextField(blank=True, default="")),
                (
                    "processing_started_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="IdempotencyKey",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="idempotency_keys",
                        to="ledger.merchant",
                    ),
                ),
                ("key", models.CharField(max_length=36)),
                ("request_fingerprint", models.CharField(max_length=64)),
                (
                    "response_status_code",
                    models.SmallIntegerField(blank=True, null=True),
                ),
                ("response_body", models.JSONField(blank=True, null=True)),
                (
                    "payout",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="idempotency_key",
                        to="payouts.payoutrequest",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(default=payouts.models._idem_expires),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="payoutrequest",
            index=models.Index(
                fields=["status", "processing_started_at"],
                name="payouts_status_proc_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="payoutrequest",
            index=models.Index(
                fields=["merchant", "-created_at"],
                name="payouts_merchant_created_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="payoutrequest",
            constraint=models.CheckConstraint(
                check=models.Q(amount_paise__gt=0),
                name="payout_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="idempotencykey",
            constraint=models.UniqueConstraint(
                fields=["merchant", "key"], name="uniq_idem_per_merchant"
            ),
        ),
        migrations.AddIndex(
            model_name="idempotencykey",
            index=models.Index(
                fields=["expires_at"], name="payouts_idem_expires_idx"
            ),
        ),
    ]
