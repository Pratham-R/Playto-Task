import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ledger", "0001_initial"),
        ("payouts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LedgerEntry",
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
                        related_name="ledger_entries",
                        to="ledger.merchant",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("CREDIT", "Credit"),
                            ("HOLD", "Hold"),
                            ("RELEASE", "Release"),
                        ],
                        max_length=10,
                    ),
                ),
                ("amount_paise", models.BigIntegerField()),
                (
                    "payout",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ledger_entries",
                        to="payouts.payoutrequest",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="ledgerentry",
            index=models.Index(
                fields=["merchant", "-created_at"],
                name="ledger_entry_merchant_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.CheckConstraint(
                check=models.Q(amount_paise__gt=0),
                name="ledger_amount_positive",
            ),
        ),
    ]
