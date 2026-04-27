from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ledger.models import BankAccount, LedgerEntry, Merchant

# Fixed IDs make seed idempotent — same run twice = same data, no duplicates.
SEED_DATA = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Acme Studio",
        "bank_accounts": [
            {
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "account_holder_name": "Acme Studio Pvt Ltd",
                "account_number_last4": "4321",
                "ifsc": "HDFC0001234",
            }
        ],
        # Total: ₹50,000 = 5,000,000 paise
        "credits": [
            {"id": "11111111-1111-1111-0000-000000000001", "amount_paise": 1_500_000, "days_ago": 10},
            {"id": "11111111-1111-1111-0000-000000000002", "amount_paise": 2_000_000, "days_ago": 7},
            {"id": "11111111-1111-1111-0000-000000000003", "amount_paise": 1_000_000, "days_ago": 4},
            {"id": "11111111-1111-1111-0000-000000000004", "amount_paise": 500_000, "days_ago": 1},
        ],
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Lotus Freelance",
        "bank_accounts": [
            {
                "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "account_holder_name": "Priya Sharma",
                "account_number_last4": "8765",
                "ifsc": "ICIC0002345",
            },
            {
                "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "account_holder_name": "Priya Sharma (Savings)",
                "account_number_last4": "9999",
                "ifsc": "ICIC0002345",
            },
        ],
        # Total: ₹1,20,000 = 12,000,000 paise
        "credits": [
            {"id": "22222222-2222-2222-0000-000000000001", "amount_paise": 5_000_000, "days_ago": 14},
            {"id": "22222222-2222-2222-0000-000000000002", "amount_paise": 4_000_000, "days_ago": 9},
            {"id": "22222222-2222-2222-0000-000000000003", "amount_paise": 3_000_000, "days_ago": 3},
        ],
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "name": "Banyan Agency",
        "bank_accounts": [
            {
                "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "account_holder_name": "Banyan Agency LLP",
                "account_number_last4": "0042",
                "ifsc": "SBIN0003456",
            }
        ],
        # Total: ₹1,000 = 100,000 paise
        # Deliberately small: concurrency test fires two 60,000-paise requests
        # against this merchant — exactly one must succeed, the other rejected.
        "credits": [
            {"id": "33333333-3333-3333-0000-000000000001", "amount_paise": 60_000, "days_ago": 5},
            {"id": "33333333-3333-3333-0000-000000000002", "amount_paise": 40_000, "days_ago": 2},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed merchants, bank accounts, and credit ledger entries (idempotent)"

    def handle(self, *args, **options):
        now = timezone.now()

        with transaction.atomic():

            seed_names = [d["name"] for d in SEED_DATA]
            fixed_ids = [d["id"] for d in SEED_DATA]
            
            duplicates = Merchant.objects.filter(name__in=seed_names).exclude(id__in=fixed_ids)
            if duplicates.exists():
                self.stdout.write(self.style.WARNING(f"Cleaning up {duplicates.count()} duplicate merchants..."))
                from payouts.models import PayoutRequest, IdempotencyKey
                IdempotencyKey.objects.filter(merchant__in=duplicates).delete()
                PayoutRequest.objects.filter(merchant__in=duplicates).delete()
                LedgerEntry.objects.filter(merchant__in=duplicates).delete()
                BankAccount.objects.filter(merchant__in=duplicates).delete()
                duplicates.delete()

            for data in SEED_DATA:
                merchant, created = Merchant.objects.update_or_create(
                    id=data["id"],
                    defaults={"name": data["name"]},
                )
                self.stdout.write(
                    f"{'Created' if created else 'Found'}: {merchant.name}"
                )

                for ba in data["bank_accounts"]:
                    BankAccount.objects.update_or_create(
                        id=ba["id"],
                        defaults={
                            "merchant": merchant,
                            "account_holder_name": ba["account_holder_name"],
                            "account_number_last4": ba["account_number_last4"],
                            "ifsc": ba["ifsc"],
                        },
                    )

                for credit in data["credits"]:
                    entry, created = LedgerEntry.objects.get_or_create(
                        id=credit["id"],
                        defaults={
                            "merchant": merchant,
                            "kind": LedgerEntry.Kind.CREDIT,
                            "amount_paise": credit["amount_paise"],
                            "created_at": now - timedelta(days=credit["days_ago"]),
                        },
                    )

        self._print_summary()

    def _print_summary(self):
        self.stdout.write("\n=== Balance Summary ===")
        for m in Merchant.objects.with_balances().order_by("name"):
            self.stdout.write(
                f"  {m.name:<20} "
                f"available=₹{m.available_paise / 100:>10,.2f}  "
                f"held=₹{m.held_paise / 100:>10,.2f}"
            )
