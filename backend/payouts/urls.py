from django.urls import path

from payouts.views import MerchantPayoutListCreateView, PayoutDetailView

urlpatterns = [
    path(
        "merchants/<uuid:merchant_id>/payouts/",
        MerchantPayoutListCreateView.as_view(),
        name="merchant-payouts",
    ),
    path(
        "payouts/<uuid:payout_id>/",
        PayoutDetailView.as_view(),
        name="payout-detail",
    ),
]
