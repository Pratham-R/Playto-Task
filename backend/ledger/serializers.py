from rest_framework import serializers

from ledger.models import BankAccount, LedgerEntry, Merchant


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["id", "account_holder_name", "account_number_last4", "ifsc"]


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ["id", "name", "created_at"]


class MerchantBalanceSerializer(serializers.Serializer):
    merchant_id = serializers.UUIDField()
    name = serializers.CharField()
    available_paise = serializers.IntegerField()
    held_paise = serializers.IntegerField()


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ["id", "kind", "amount_paise", "payout_id", "created_at"]
