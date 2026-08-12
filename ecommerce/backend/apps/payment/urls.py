from django.urls import path

from .views import PaymentCallbackView, PaymentInitiateView, PaymentMethodsView, PaymentStatusView

urlpatterns = [
    path("payment-methods", PaymentMethodsView.as_view()),
    path("payment/<uuid:order_id>/initiate", PaymentInitiateView.as_view()),
    path("payment/callback/<str:gateway>", PaymentCallbackView.as_view()),
    path("payment/<uuid:order_id>/status", PaymentStatusView.as_view()),
]
