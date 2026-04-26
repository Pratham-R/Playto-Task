from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.models import Merchant
from payouts.models import PayoutRequest
from payouts.serializers import CreatePayoutSerializer, PayoutSerializer
from payouts.services import (
    BodyMismatch,
    InsufficientFundsError,
    create_payout_atomic,
    fingerprint,
    get_or_create_idem_key,
)


class MerchantPayoutListCreateView(APIView):
    """
    GET  /api/v1/merchants/{merchant_id}/payouts/  — payout history
    POST /api/v1/merchants/{merchant_id}/payouts/  — request a payout
    """

    def get(self, request, merchant_id):
        get_object_or_404(Merchant, id=merchant_id)
        payouts = (
            PayoutRequest.objects.filter(merchant_id=merchant_id)
            .order_by("-created_at")[:50]
        )
        return Response(PayoutSerializer(payouts, many=True).data)

    def post(self, request, merchant_id):
        idem_key_str = request.headers.get("Idempotency-Key", "").strip()
        if not idem_key_str:
            return Response(
                {"error": "Idempotency-Key header is required"}, status=400
            )

        serializer = CreatePayoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        amount_paise = serializer.validated_data["amount_paise"]
        bank_account_id = serializer.validated_data["bank_account_id"]

        # Canonical body for fingerprinting — must match what client signs
        body = {
            "amount_paise": amount_paise,
            "bank_account_id": str(bank_account_id),
        }
        fp = fingerprint(body)

        get_object_or_404(Merchant, id=merchant_id)

        # ── Idempotency gate ──────────────────────────────────────────────────
        try:
            idem, is_new = get_or_create_idem_key(merchant_id, idem_key_str, fp)
        except BodyMismatch:
            return Response(
                {"error": "body_mismatch_for_idempotency_key"}, status=409
            )

        if not is_new:
            if idem.response_status_code is None:
                # First request still in flight
                return Response({"error": "request_in_flight"}, status=409)
            # Replay cached response exactly
            return Response(idem.response_body, status=idem.response_status_code)

        # ── New request — run atomic lock + balance check + create ────────────
        payout = None
        try:
            payout = create_payout_atomic(merchant_id, bank_account_id, amount_paise)
        except InsufficientFundsError as exc:
            response_data = {"error": "insufficient_funds", "detail": str(exc)}
            status_code = 422
        except ValueError as exc:
            response_data = {"error": "invalid_request", "detail": str(exc)}
            status_code = 400
        except Merchant.DoesNotExist:
            response_data = {"error": "merchant_not_found"}
            status_code = 404
        else:
            response_data = PayoutSerializer(payout).data
            status_code = 201

        # Store response so future replays return the same thing
        idem.response_status_code = status_code
        idem.response_body = response_data
        if payout is not None:
            idem.payout = payout
        idem.save(update_fields=["response_status_code", "response_body", "payout_id"])

        return Response(response_data, status=status_code)


class PayoutDetailView(APIView):
    """GET /api/v1/payouts/{payout_id}/"""

    def get(self, request, payout_id):
        payout = get_object_or_404(PayoutRequest, id=payout_id)
        return Response(PayoutSerializer(payout).data)
