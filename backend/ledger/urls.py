from django.urls import path

from ledger.views import (
    MerchantBalanceView,
    MerchantBankAccountsView,
    MerchantLedgerView,
    MerchantListView,
)

urlpatterns = [
    path("merchants/", MerchantListView.as_view(), name="merchant-list"),
    path(
        "merchants/<uuid:merchant_id>/balance/",
        MerchantBalanceView.as_view(),
        name="merchant-balance",
    ),
    path(
        "merchants/<uuid:merchant_id>/ledger/",
        MerchantLedgerView.as_view(),
        name="merchant-ledger",
    ),
    path(
        "merchants/<uuid:merchant_id>/bank-accounts/",
        MerchantBankAccountsView.as_view(),
        name="merchant-bank-accounts",
    ),
]
