from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.models import LedgerEntry, Merchant
from ledger.serializers import (
    BankAccountSerializer,
    LedgerEntrySerializer,
    MerchantBalanceSerializer,
    MerchantSerializer,
)


class MerchantListView(APIView):
    """GET /api/v1/merchants/"""

    def get(self, request):
        merchants = Merchant.objects.with_balances().order_by("name")
        data = [
            {
                "merchant_id": m.id,
                "name": m.name,
                "available_paise": m.available_paise,
                "held_paise": m.held_paise,
            }
            for m in merchants
        ]
        return Response(data)


class MerchantBalanceView(APIView):
    """GET /api/v1/merchants/{merchant_id}/balance/"""

    def get(self, request, merchant_id):
        merchant = (
            Merchant.objects.with_balances()
            .filter(id=merchant_id)
            .first()
        )
        if not merchant:
            return Response({"error": "merchant_not_found"}, status=404)
        data = {
            "merchant_id": merchant.id,
            "name": merchant.name,
            "available_paise": merchant.available_paise,
            "held_paise": merchant.held_paise,
        }
        return Response(MerchantBalanceSerializer(data).data)


class MerchantLedgerView(APIView):
    """GET /api/v1/merchants/{merchant_id}/ledger/"""

    def get(self, request, merchant_id):
        get_object_or_404(Merchant, id=merchant_id)
        entries = (
            LedgerEntry.objects.filter(merchant_id=merchant_id)
            .order_by("-created_at")
            .select_related("payout")[:100]
        )
        return Response(LedgerEntrySerializer(entries, many=True).data)


class MerchantBankAccountsView(APIView):
    """GET /api/v1/merchants/{merchant_id}/bank-accounts/"""

    def get(self, request, merchant_id):
        merchant = get_object_or_404(Merchant, id=merchant_id)
        accounts = merchant.bank_accounts.all()
        return Response(BankAccountSerializer(accounts, many=True).data)
