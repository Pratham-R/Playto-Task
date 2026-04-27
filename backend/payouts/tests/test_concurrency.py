import json
import threading
import uuid
from unittest.mock import patch

from django.test import Client, TransactionTestCase

from ledger.models import BankAccount, LedgerEntry, Merchant
from payouts.models import PayoutRequest


class ConcurrencyTest(TransactionTestCase):
    """
    TransactionTestCase (not TestCase) is required here.
    TestCase wraps every test in a transaction that never commits, so threads
    cannot see each other's writes. TransactionTestCase lets each DB operation
    commit for real, which means the SELECT FOR UPDATE lock actually serializes
    the two concurrent requests the same way it would in production.
    """

    def setUp(self):
        # Prevent Celery from trying to connect to Redis during tests.
        self.enqueue_patcher = patch("payouts.services._enqueue_process_payout")
        self.enqueue_patcher.start()

        self.merchant = Merchant.objects.create(name="Banyan Agency Test")
        self.bank = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Banyan Agency LLP",
            account_number_last4="0042",
            ifsc="SBIN0003456",
        )
        # Exactly ₹1,000 = 100,000 paise — two 60,000 paise requests can't both fit
        LedgerEntry.objects.create(
            merchant=self.merchant,
            kind=LedgerEntry.Kind.CREDIT,
            amount_paise=100_000,
        )

    def tearDown(self):
        self.enqueue_patcher.stop()

    def test_two_simultaneous_requests_exactly_one_wins(self):
        """
        Two concurrent payout requests of 60,000 paise against a 100,000 paise
        balance. The SELECT FOR UPDATE lock serializes them at the DB level.
        Exactly one must succeed (201) and the other must be rejected (422).
        """
        url = f"/api/v1/merchants/{self.merchant.id}/payouts/"
        results = []
        barrier = threading.Barrier(2)  # both threads release together

        def make_request(idem_key):
            client = Client()
            barrier.wait()  # maximise race window — both threads hit the view simultaneously
            resp = client.post(
                url,
                data=json.dumps(
                    {"amount_paise": 60_000, "bank_account_id": str(self.bank.id)}
                ),
                content_type="application/json",
                HTTP_IDEMPOTENCY_KEY=idem_key,
            )
            results.append(resp.status_code)

        t1 = threading.Thread(target=make_request, args=[str(uuid.uuid4())])
        t2 = threading.Thread(target=make_request, args=[str(uuid.uuid4())])
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly one success, one rejection
        self.assertEqual(sorted(results), [201, 422])

        # Only one PayoutRequest row created — no ghost payout
        self.assertEqual(PayoutRequest.objects.count(), 1)

        # Balance invariant: credits − holds + releases == available + held
        merchant = Merchant.objects.with_balances().get(id=self.merchant.id)
        self.assertEqual(
            merchant.available_paise + merchant.held_paise,
            100_000,
            "available + held must always equal total credits",
        )
        # Balance must never go negative
        self.assertGreaterEqual(merchant.available_paise, 0)
