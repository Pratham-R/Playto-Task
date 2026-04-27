import json
import uuid
from unittest.mock import patch

from django.test import Client, TestCase

from ledger.models import BankAccount, LedgerEntry, Merchant
from payouts.models import IdempotencyKey, PayoutRequest


class IdempotencyTest(TestCase):

    def setUp(self):
        self.enqueue_patcher = patch("payouts.services._enqueue_process_payout")
        self.enqueue_patcher.start()

        self.merchant = Merchant.objects.create(name="Idempotency Test Merchant")
        self.bank = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Test Account",
            account_number_last4="9999",
            ifsc="HDFC0001234",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            kind=LedgerEntry.Kind.CREDIT,
            amount_paise=500_000,  # ₹5,000
        )
        self.url = f"/api/v1/merchants/{self.merchant.id}/payouts/"
        self.client = Client()

    def tearDown(self):
        self.enqueue_patcher.stop()

    def _post(self, idem_key, amount_paise=10_000):
        return self.client.post(
            self.url,
            data=json.dumps(
                {"amount_paise": amount_paise, "bank_account_id": str(self.bank.id)}
            ),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=idem_key,
        )

    def test_same_key_returns_identical_response(self):
        """Second call with same key must return exact same body and status."""
        key = str(uuid.uuid4())

        r1 = self._post(key)
        r2 = self._post(key)

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.status_code, r2.status_code)
        self.assertEqual(r1.json(), r2.json())

    def test_same_key_creates_only_one_payout(self):
        """No duplicate PayoutRequest row even after calling twice."""
        key = str(uuid.uuid4())
        self._post(key)
        self._post(key)

        self.assertEqual(PayoutRequest.objects.count(), 1)
        self.assertEqual(IdempotencyKey.objects.count(), 1)

    def test_same_key_different_body_returns_409(self):
        """Reusing a key with a different amount must be rejected as 409 Conflict."""
        key = str(uuid.uuid4())

        r1 = self._post(key, amount_paise=10_000)
        r2 = self._post(key, amount_paise=20_000)  # different body

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 409)
        self.assertIn("body_mismatch", r2.json()["error"])

    def test_missing_idempotency_key_header_returns_400(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"amount_paise": 10_000, "bank_account_id": str(self.bank.id)}),
            content_type="application/json",
            # no Idempotency-Key header
        )
        self.assertEqual(resp.status_code, 400)

    def test_insufficient_funds_response_is_also_idempotent(self):
        """Even a failed (422) response must be replayed identically on retry."""
        key = str(uuid.uuid4())

        r1 = self._post(key, amount_paise=999_999_999)  # way more than balance
        r2 = self._post(key, amount_paise=999_999_999)

        self.assertEqual(r1.status_code, 422)
        self.assertEqual(r2.status_code, 422)
        self.assertEqual(r1.json(), r2.json())
        self.assertEqual(PayoutRequest.objects.count(), 0)  # no payout created
