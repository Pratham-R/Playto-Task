# Playto Payout Engine — EXPLAINER.md

---

## 1. The Ledger

### Why append-only?

Every rupee movement is a new row. Nothing ever gets updated or deleted. I chose this because it gives you a full audit trail for free — if something goes wrong at 2am, you can replay entries up to any timestamp and know exactly what the balance was at that moment. Reversals are just new rows, not mutations of old ones.

There are three entry types:

| Kind    | When it's written                    | What it does to available balance |
|---------|--------------------------------------|-----------------------------------|
| CREDIT  | Customer payment arrives (seeded)    | +amount                           |
| HOLD    | Payout enters pending                | −amount (funds reserved)          |
| RELEASE | Payout fails after being held        | +amount (funds returned)          |

One design decision worth noting: when a payout succeeds, the original HOLD just stays there permanently — it becomes the final debit. I didn't add a separate CAPTURE or DEBIT entry type. Simpler model, cleaner audit trail, same math.

Everything is stored as `BigIntegerField` in paise. ₹1 = 100 paise. No floats, no Decimals. There's no rounding error possible when you're doing integer arithmetic.

### The balance query

```python
# ledger/managers.py
class MerchantQuerySet(models.QuerySet):
    def with_balances(self):
        zero = Value(0, output_field=BigIntegerField())
        return self.annotate(
            credit_total=Coalesce(
                Sum("ledger_entries__amount_paise", filter=Q(ledger_entries__kind="CREDIT")),
                zero,
            ),
            hold_total=Coalesce(
                Sum("ledger_entries__amount_paise", filter=Q(ledger_entries__kind="HOLD")),
                zero,
            ),
            release_total=Coalesce(
                Sum("ledger_entries__amount_paise", filter=Q(ledger_entries__kind="RELEASE")),
                zero,
            ),
        ).annotate(
            available_paise=F("credit_total") - F("hold_total") + F("release_total"),
            held_paise=F("hold_total") - F("release_total"),
        )
```

Balance is never computed in Python. It's a single SQL aggregation — the database does the math, Django just reads the result. The invariant this enforces: `available_paise + held_paise == credit_total`. The concurrency test asserts this holds even under simultaneous payout requests.

---

## 2. The Lock — Preventing Double-Spend

### The problem

Merchant has ₹1,000. Two payout requests for ₹600 each arrive at the same millisecond. Both read the balance as ₹1,000. Both pass the check. Both write a HOLD. You've just paid out ₹1,200 from a ₹1,000 balance. This is the classic TOCTOU bug — time-of-check to time-of-use.

### The fix

```python
# payouts/services.py
@transaction.atomic
def create_payout_atomic(merchant_id, bank_account_id, amount_paise: int) -> PayoutRequest:
    # This line is the whole fix.
    # Postgres acquires an exclusive row-level lock on this merchant's DB row.
    # The second concurrent request blocks here until the first transaction commits.
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)

    available = _available_paise(merchant_id)   # re-read inside the lock
    if available < amount_paise:
        raise InsufficientFundsError(...)

    payout = PayoutRequest.objects.create(...)
    LedgerEntry.objects.create(kind=LedgerEntry.Kind.HOLD, ...)

    # Defer the Celery enqueue until after the transaction commits.
    # Without this, the worker could receive the task and try to read the payout
    # row before it's actually on disk.
    payout_id = str(payout.id)
    transaction.on_commit(lambda: _enqueue_process_payout(payout_id))

    return payout
```

Here's what actually happens with two concurrent requests:

1. Request A hits `select_for_update()` — Postgres locks the merchant row
2. Request B hits the same line — Postgres makes it wait
3. Request A checks balance (₹1,000), writes a HOLD for ₹600, commits. Lock released
4. Request B unblocks, re-reads balance (now ₹400), tries ₹600 → `InsufficientFundsError` → 422

The lock is per merchant row, so two different merchants don't block each other. Only same-merchant requests serialize.

The `transaction.on_commit` was a non-obvious thing I had to think about. If you call `task.delay()` inside the transaction and the transaction rolls back, Celery has already received the task ID and will try to fetch a payout row that doesn't exist. `on_commit` defers the enqueue until the write is durable.

---

## 3. Idempotency

### The goal

Networks fail. A client sends a payout request, we process it and write the HOLD, but the response never makes it back. Client retries. Without idempotency, that's a second HOLD on the same funds. The client just withdrew twice.

### How it works

Every POST must include an `Idempotency-Key` UUID header. The flow:

1. Compute a SHA-256 fingerprint of the canonical request body (keys sorted, no whitespace)
2. Call `get_or_create(merchant_id, key_str, defaults={fingerprint: fp})`
3. **New key** (`created=True`): run the real logic, store the response status + body on the row
4. **Known key** (`created=False`): return the cached response — no DB writes, no Celery task

```python
# payouts/views.py (simplified)
idem, is_new = get_or_create_idem_key(merchant_id, idem_key_str, fp)

if not is_new:
    if idem.response_status_code is None:
        return Response({"error": "request_in_flight"}, status=409)
    return Response(idem.response_body, status=idem.response_status_code)

# ... run create_payout_atomic ...
idem.response_status_code = status_code
idem.response_body = json.loads(JSONRenderer().render(response_data))
idem.save(update_fields=["response_status_code", "response_body", "payout_id"])
```

Two edge cases I specifically handled:

**Body mismatch:** same key, different request body → 409 Conflict. The key is scoped to a specific request, not just a deduplication token.

**In-flight sentinel:** `response_status_code=NULL` means the first request is still executing. If a retry arrives before the first call completes, it gets a 409 `request_in_flight` instead of accidentally running the create logic in parallel. Two simultaneous first-time requests with the same key both hit `get_or_create` — the `UniqueConstraint(merchant, key)` means only one INSERT wins. The loser gets an `IntegrityError`, catches it, falls through to read the winner's row, and returns the cached response.

One more thing: even failed responses are cached. If the first call returns 422 (insufficient funds), that 422 is stored. Retries replay it — no second attempt at the payout.

---

## 4. The State Machine

### Why it exists

Without it, a Celery worker and a stuck-retry scanner can race to finalize the same payout. Worker marks it COMPLETED. Scanner also picks it up, marks it FAILED, writes a RELEASE entry, and incorrectly returns the funds to the merchant. Double-spend in reverse.

### The implementation

```python
# payouts/state_machine.py
_ALLOWED: dict[str, set[str]] = {
    PayoutRequest.Status.PENDING:    {PayoutRequest.Status.PROCESSING},
    PayoutRequest.Status.PROCESSING: {PayoutRequest.Status.COMPLETED, PayoutRequest.Status.FAILED},
    PayoutRequest.Status.COMPLETED:  set(),   # terminal — nothing allowed out
    PayoutRequest.Status.FAILED:     set(),   # terminal — nothing allowed out
}

def transition(payout: PayoutRequest, to_status: str) -> None:
    allowed = _ALLOWED.get(payout.status, set())
    if to_status not in allowed:
        raise InvalidTransition(
            f"Transition {payout.status!r} → {to_status!r} is not allowed"
        )
    payout.status = to_status
```

`FAILED → COMPLETED` is blocked here — `_ALLOWED[FAILED]` is an empty set, so any transition out of FAILED raises `InvalidTransition`. Same for COMPLETED. Both are terminal states with no exits.

There's no `payout.status = "COMPLETED"` anywhere else in the codebase. Every status change goes through `transition()`. The race condition between two workers is handled by combining this with a `select_for_update()` inside the finalizer:

```python
def _complete_payout(payout_id):
    with transaction.atomic():
        payout = PayoutRequest.objects.select_for_update().get(id=payout_id)
        try:
            transition(payout, PayoutRequest.Status.COMPLETED)
        except InvalidTransition:
            return  # Another worker already finalized this — walk away
        payout.save(update_fields=["status", "updated_at"])
```

First worker transitions and saves. Second worker unblocks, calls `transition()`, gets `InvalidTransition` because the status is already terminal, returns without writing anything.

---

## 5. AI Audit — A Bug I Actually Caught

When writing the idempotency caching step, the AI gave me this:

```python
# What the AI wrote
idem.response_body = PayoutSerializer(payout).data  # stores a ReturnDict
idem.save(update_fields=["response_status_code", "response_body", "payout_id"])
```

Looks fine. It's a dict, JSONField takes dicts, should work. It didn't.

```
TypeError: Object of type UUID is not JSON serializable
```

The issue: DRF's `ReturnDict` is a dict subclass, but it hasn't been through a JSON encoder yet. It still contains raw Python objects — `uuid.UUID` instances for ID fields, `datetime` objects for timestamps. When Postgres's JSONField calls `json.dumps()` internally before writing to the `jsonb` column, Python's encoder doesn't know how to handle UUID or datetime.

The AI conflated "dict-like" with "JSON-serializable". These are not the same thing.

The fix:

```python
# What I replaced it with
idem.response_body = json.loads(JSONRenderer().render(response_data))
idem.save(update_fields=["response_status_code", "response_body", "payout_id"])
```

`JSONRenderer().render()` runs DRF's full encoder — it handles UUID, datetime, Decimal, everything — and returns bytes. `json.loads()` converts those bytes back to a plain Python dict with only JSON-native types. That goes into the JSONField safely.

This fix works for all response shapes — success responses with UUID fields, error dicts like `{"error": "insufficient_funds"}` — so no special-casing needed anywhere.