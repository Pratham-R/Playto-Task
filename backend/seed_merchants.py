import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playto.settings')
django.setup()

from ledger.models import Merchant, LedgerEntry

def seed():
    data = [
        {"name": "Acme Studio", "balance": 5000000},
        {"name": "Lotus Freelance", "balance": 12000000},
        {"name": "Banyan Agency", "balance": 100000},
    ]

    for item in data:
        merchant, created = Merchant.objects.get_or_create(name=item["name"])
        if created:
            print(f"Created merchant: {item['name']}")
            # Give initial balance via CREDIT
            LedgerEntry.objects.create(
                merchant=merchant,
                kind=LedgerEntry.Kind.CREDIT,
                amount_paise=item["balance"]
            )
            print(f"Added initial balance of {item['balance']}p to {item['name']}")
        else:
            print(f"Merchant {item['name']} already exists, skipping.")

if __name__ == "__main__":
    seed()
