from django.urls import path

from . import views

urlpatterns = [
    path("products/<uuid:product_id>/reviews", views.ProductReviewListView.as_view()),
    path("order-items/<uuid:order_item_id>/review", views.CustomerReviewCreateView.as_view()),
    path("reviews/<uuid:review_id>", views.CustomerReviewUpdateView.as_view()),
    path("seller/reviews", views.SellerReviewListView.as_view()),
    path("seller/reviews/<uuid:review_id>/reply", views.SellerReviewReplyView.as_view()),
    path("seller/reviews/<uuid:review_id>/report", views.SellerReviewReportView.as_view()),
    path("admin/review-reports", views.AdminReviewReportListView.as_view()),
    path(
        "admin/review-reports/<uuid:report_id>/resolve",
        views.AdminReviewReportResolveView.as_view(),
    ),
]
