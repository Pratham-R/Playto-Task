import random
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from ledger.models import LedgerEntry
from payouts.models import PayoutRequest
from payouts.state_machine import InvalidTransition, transition


@shared_task(bind=True, name="payouts.process_payout", max_retries=0)
def process_payout(self, payout_id: str) -> None:
    """
    Moves a payout through its lifecycle:
      PENDING → PROCESSING → COMPLETED  (70 % of the time)
                           → FAILED     (20 % — releases held funds atomically)
      hangs in PROCESSING               (10 % — retry_stuck_payouts re-queues it)
    """
    with transaction.atomic():
        try:
            payout = (
                PayoutRequest.objects
                .select_for_update()
                .get(id=payout_id)
            )
        except PayoutRequest.DoesNotExist:
            return

        if payout.status not in (
            PayoutRequest.Status.PENDING,
            PayoutRequest.Status.PROCESSING,
        ):
            return

        if payout.status == PayoutRequest.Status.PENDING:
            transition(payout, PayoutRequest.Status.PROCESSING)

        payout.processing_started_at = timezone.now()
        payout.attempts += 1
        payout.save(update_fields=["status", "processing_started_at", "attempts", "updated_at"])

    roll = random.random()

    if roll < 0.70:
        _complete_payout(payout_id)
    elif roll < 0.90:
        _fail_payout(payout_id, reason="Bank declined the transfer")


def _complete_payout(payout_id: str) -> None:
    with transaction.atomic():
        try:
            payout = PayoutRequest.objects.select_for_update().get(id=payout_id)
        except PayoutRequest.DoesNotExist:
            return
        try:
            transition(payout, PayoutRequest.Status.COMPLETED)
        except InvalidTransition:
            return
        payout.save(update_fields=["status", "updated_at"])


def _fail_payout(payout_id: str, reason: str = "") -> None:
    """Fail a payout and release its held funds in a single atomic transaction."""
    with transaction.atomic():
        try:
            payout = PayoutRequest.objects.select_for_update().get(id=payout_id)
        except PayoutRequest.DoesNotExist:
            return
        try:
            transition(payout, PayoutRequest.Status.FAILED)
        except InvalidTransition:
            return
        payout.last_error = reason
        payout.save(update_fields=["status", "last_error", "updated_at"])
        LedgerEntry.objects.create(
            merchant_id=payout.merchant_id,
            kind=LedgerEntry.Kind.RELEASE,
            amount_paise=payout.amount_paise,
            payout=payout,
        )


@shared_task(name="payouts.retry_stuck_payouts")
def retry_stuck_payouts() -> None:
    """
    Periodic task (every 15 s via Celery beat).
    Finds payouts stuck in PROCESSING for > 30 s and either retries them
    (exponential backoff, max 3 attempts) or fails them and releases funds.
    skip_locked=True lets multiple beat workers run safely in parallel.
    """
    cutoff = timezone.now() - timedelta(seconds=30)

    with transaction.atomic():
        stuck = list(
            PayoutRequest.objects
            .select_for_update(skip_locked=True)
            .filter(
                status=PayoutRequest.Status.PROCESSING,
                processing_started_at__lt=cutoff,
            )
        )

        for payout in stuck:
            if payout.attempts >= 3:
                transition(payout, PayoutRequest.Status.FAILED)
                payout.last_error = "Max retry attempts (3) exceeded"
                payout.save(update_fields=["status", "last_error", "updated_at"])
                LedgerEntry.objects.create(
                    merchant_id=payout.merchant_id,
                    kind=LedgerEntry.Kind.RELEASE,
                    amount_paise=payout.amount_paise,
                    payout=payout,
                )
            else:
                backoff = 2 ** payout.attempts
                payout.processing_started_at = timezone.now() + timedelta(
                    seconds=backoff + 30
                )
                payout.save(update_fields=["processing_started_at"])

                _schedule_retry(str(payout.id), backoff)


def _schedule_retry(payout_id: str, countdown: int) -> None:
    transaction.on_commit(
        lambda: process_payout.apply_async(args=[payout_id], countdown=countdown)
    )
