from django.contrib import admin

from .models import BankAccount, LedgerEntry, Merchant


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ["account_holder_name", "merchant", "ifsc", "account_number_last4"]
    list_filter = ["merchant"]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["merchant", "kind", "amount_paise", "payout_id", "created_at"]
    list_filter = ["kind", "merchant"]
    readonly_fields = ["id", "merchant", "kind", "amount_paise", "payout", "created_at"]
