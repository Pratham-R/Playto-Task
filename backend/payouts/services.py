import hashlib
import json

from django.db import IntegrityError, transaction
from django.db.models import BigIntegerField, Case, F, Sum, Value, When
from django.db.models.functions import Coalesce

from ledger.models import BankAccount, LedgerEntry, Merchant
from payouts.models import IdempotencyKey, PayoutRequest


class InsufficientFundsError(Exception):
    pass


class BodyMismatch(Exception):
    pass


def fingerprint(body: dict) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_or_create_idem_key(merchant_id, key_str: str, fp: str):
    """
    Returns (IdempotencyKey, is_new).
    Raises BodyMismatch if key exists with a different request body.
    """
    try:
        idem, created = IdempotencyKey.objects.get_or_create(
            merchant_id=merchant_id,
            key=key_str,
            defaults={"request_fingerprint": fp},
        )
    except IntegrityError:
        # Two simultaneous first-time requests — loser retries the read.
        idem = IdempotencyKey.objects.get(merchant_id=merchant_id, key=key_str)
        created = False

    if not created and idem.request_fingerprint != fp:
        raise BodyMismatch()

    return idem, created


def _available_paise(merchant_id) -> int:
    """Compute available balance via single DB aggregation. Must run inside a lock."""
    result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
        total=Coalesce(
            Sum(
                Case(
                    When(kind=LedgerEntry.Kind.CREDIT, then=F("amount_paise")),
                    When(kind=LedgerEntry.Kind.HOLD, then=-F("amount_paise")),
                    When(kind=LedgerEntry.Kind.RELEASE, then=F("amount_paise")),
                    output_field=BigIntegerField(),
                )
            ),
            Value(0, output_field=BigIntegerField()),
        )
    )
    return result["total"]


@transaction.atomic
def create_payout_atomic(merchant_id, bank_account_id, amount_paise: int) -> PayoutRequest:
    """
    Acquires a row-level FOR UPDATE lock on Merchant, then checks balance and
    writes PayoutRequest + HOLD ledger entry atomically.

    The FOR UPDATE lock serializes concurrent payout requests for the same
    merchant: the second request blocks at this SELECT until the first
    transaction commits, then re-reads the balance (which now reflects the
    first HOLD) and is correctly rejected if funds are insufficient.
    """
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)

    available = _available_paise(merchant_id)
    if available < amount_paise:
        raise InsufficientFundsError(
            f"Insufficient funds: available={available}p, requested={amount_paise}p"
        )

    try:
        bank_account = BankAccount.objects.get(id=bank_account_id, merchant=merchant)
    except BankAccount.DoesNotExist:
        raise ValueError(f"bank_account {bank_account_id} not found for this merchant")

    payout = PayoutRequest.objects.create(
        merchant=merchant,
        bank_account=bank_account,
        amount_paise=amount_paise,
        status=PayoutRequest.Status.PENDING,
    )
    LedgerEntry.objects.create(
        merchant=merchant,
        kind=LedgerEntry.Kind.HOLD,
        amount_paise=amount_paise,
        payout=payout,
    )

    # Queue processing only after DB transaction commits — avoids task reading
    # a payout row that doesn't exist yet if the transaction rolls back.
    payout_id = str(payout.id)
    transaction.on_commit(
        lambda: _enqueue_process_payout(payout_id)
    )

    return payout


def _enqueue_process_payout(payout_id: str) -> None:
    # Lazy import breaks the services ↔ tasks circular dependency.
    from payouts.tasks import process_payout  # noqa: PLC0415
    process_payout.delay(payout_id)
