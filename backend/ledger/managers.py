from django.db import models
from django.db.models import BigIntegerField, F, Q, Sum, Value
from django.db.models.functions import Coalesce


class MerchantQuerySet(models.QuerySet):
    def with_balances(self):
        zero = Value(0, output_field=BigIntegerField())
        return self.annotate(
            credit_total=Coalesce(
                Sum(
                    "ledger_entries__amount_paise",
                    filter=Q(ledger_entries__kind="CREDIT"),
                ),
                zero,
            ),
            hold_total=Coalesce(
                Sum(
                    "ledger_entries__amount_paise",
                    filter=Q(ledger_entries__kind="HOLD"),
                ),
                zero,
            ),
            release_total=Coalesce(
                Sum(
                    "ledger_entries__amount_paise",
                    filter=Q(ledger_entries__kind="RELEASE"),
                ),
                zero,
            ),
        ).annotate(
            # available = credits − net holds (holds not yet released)
            available_paise=F("credit_total") - F("hold_total") + F("release_total"),
            # held = holds still outstanding (pending/processing payouts)
            held_paise=F("hold_total") - F("release_total"),
        )


class MerchantManager(models.Manager):
    def get_queryset(self):
        return MerchantQuerySet(self.model, using=self._db)

    def with_balances(self):
        return self.get_queryset().with_balances()
