#!/bin/bash

# Exit on error
set -e

echo "--- Running Migrations ---"
python manage.py migrate

echo "--- Starting Celery Worker ---"
# --concurrency 1 to keep memory usage low
celery -A playto worker -l info --concurrency 1 &

echo "--- Starting Celery Beat ---"
celery -A playto beat -l info &

echo "--- Seeding Data ---"
python manage.py shell -c "from ledger.models import Merchant; Merchant.objects.get_or_create(name='Test Merchant', defaults={'email': 'test@example.com'})"

echo "--- Starting Gunicorn ---"
# Port is provided by Railway environment
gunicorn playto.wsgi --bind 0.0.0.0:${PORT:-8000}
