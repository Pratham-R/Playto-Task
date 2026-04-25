# Playto Payout Engine

Cross-border payout engine for Indian merchants. Merchants accumulate balance from simulated international payments and withdraw to Indian bank accounts.

## Stack
- **Backend**: Django 5.2 + DRF, PostgreSQL, Celery + Redis
- **Frontend**: React + Vite + Tailwind

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, REDIS_URL

# Create database
createdb playto

# Run migrations
python manage.py migrate

# Seed test data (3 merchants, credit history)
python manage.py seed

# Start dev server
python manage.py runserver

# Start Celery worker
celery -A playto worker -l info

# Start Celery beat
celery -A playto beat -l info
```

### Running tests

```bash
cd backend
pytest
# single test file
pytest payouts/tests/test_concurrency.py -v
```

## Merchant test data (seeded)

| Merchant | Balance | Purpose |
|---|---|---|
| Acme Studio | ₹50,000 | General testing |
| Lotus Freelance | ₹1,20,000 | Large balance testing |
| Banyan Agency | ₹1,000 | Concurrency test (two ₹600 requests) |

## Architecture notes

See `EXPLAINER.md` for the decisions behind the ledger model, locking strategy, idempotency design, and state machine enforcement.
