from django.urls import path

from . import views

urlpatterns = [
    path("orders/<uuid:order_id>/return-request", views.CustomerReturnRequestView.as_view()),
    path(
        "return-requests/<uuid:return_request_id>/escalate",
        views.CustomerReturnEscalateView.as_view(),
    ),
    path("seller/return-requests", views.SellerReturnRequestListView.as_view()),
    path(
        "seller/return-requests/<uuid:return_request_id>/decision",
        views.SellerReturnDecisionView.as_view(),
    ),
    path("admin/disputes", views.AdminDisputeListView.as_view()),
    path("admin/disputes/<uuid:dispute_id>", views.AdminDisputeDetailView.as_view()),
    path(
        "admin/disputes/<uuid:dispute_id>/review",
        views.AdminDisputeReviewView.as_view(),
    ),
    path("admin/disputes/<uuid:dispute_id>/resolve", views.AdminDisputeResolveView.as_view()),
]
