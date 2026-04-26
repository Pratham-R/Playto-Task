# Playto Payout Engine 🚀

A robust cross-border payout engine for Indian merchants. This platform enables merchants to manage balances accumulated from international payments and securely withdraw them to Indian bank accounts using a double-entry ledger system.

## 🏗 Architecture & Features

- **Double-Entry Ledger**: Every transaction is tracked with `CREDIT`, `HOLD`, and `RELEASE` entries to ensure 100% financial accuracy.
- **Atomic Concurrency Control**: Uses PostgreSQL row-level locking (`select_for_update`) to prevent double-spending or balance inconsistencies.
- **Idempotent Payouts**: Guaranteed "exactly-once" processing using merchant-supplied idempotency keys.
- **State Machine Workflow**: Payouts follow a strict lifecycle (`PENDING` → `PROCESSING` → `COMPLETED` / `FAILED`).
- **Background Processing**: Long-running payout simulations are handled asynchronously via Celery and Redis.

## 💻 Tech Stack

- **Backend**: Django 5.x + Django REST Framework, PostgreSQL
- **Async Tasks**: Celery + Redis
- **Frontend**: Next.js 14 (App Router) + Tailwind CSS
- **Testing**: Pytest for backend concurrency and logic validation

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL
- Redis

### 2. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, REDIS_URL

# Setup Database
createdb playto
python manage.py migrate

# Seed Test Data (3 merchants with varying balances)
python manage.py seed

# Start Services (in separate terminals)
python manage.py runserver
celery -A playto worker -l info
celery -A playto beat -l info
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 🧪 Testing

The backend includes comprehensive tests for core logic and concurrency.

```bash
cd backend
pytest

# Test concurrency specifically (race conditions)
pytest payouts/tests/test_concurrency.py -v
```

---

## 📊 Merchant Test Data (Seeded)

| Merchant | Initial Balance | Use Case |
|---|---|---|
| **Acme Studio** | ₹50,000 | General workflow testing |
| **Lotus Freelance** | ₹1,20,000 | Large withdrawal testing |
| **Banyan Agency** | ₹1,000 | Concurrency / Race-condition testing |

---

## 📖 Project Documentation

For a deeper dive into specific implementation decisions (Ledger vs. Balance, Locking strategies, Idempotency design), please refer to the `EXPLAINER.md`.

