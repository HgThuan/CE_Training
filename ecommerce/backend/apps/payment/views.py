from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.account.permissions import IsCustomer
from apps.common.responses import success_response
from apps.order.models import Order

from .serializers import PaymentStatusSerializer
from .services import PaymentService


class CallbackThrottle(AnonRateThrottle):
    scope = "payment_callback"


class PaymentMethodsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return success_response(
            data=[
                {"code": Order.PaymentMethod.COD, "name": "Thanh toán khi nhận hàng"},
                {"code": Order.PaymentMethod.VNPAY, "name": "VNPay Sandbox"},
            ]
        )


class PaymentInitiateView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, customer__user=request.user)
        payment, url = PaymentService.create_payment_intent(order)
        return success_response(
            data={"payment": PaymentStatusSerializer(payment).data, "payment_url": url},
            message="Đã khởi tạo thanh toán",
        )


class PaymentCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CallbackThrottle]

    def post(self, request, gateway):
        payload = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)
        payment = PaymentService.handle_callback(gateway, payload)
        if gateway.lower() == "vnpay":
            return Response({"RspCode": "00", "Message": "Confirm Success"})
        return success_response(
            data={"payment_code": payment.payment_code, "status": payment.status},
            message="Callback đã được ghi nhận",
        )

    def get(self, request, gateway):
        payment = PaymentService.handle_callback(gateway, request.query_params.dict())
        if gateway.lower() == "vnpay":
            return Response({"RspCode": "00", "Message": "Confirm Success"})
        return success_response(
            data={"payment_code": payment.payment_code, "status": payment.status},
            message="Callback đã được ghi nhận",
        )


class PaymentStatusView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, customer__user=request.user)
        payment = order.payments.order_by("-created_at").first()
        data = {
            "order_id": str(order.pk),
            "order_code": order.order_code,
            "payment_status": order.payment_status,
            "payment_method": order.payment_method,
            "payment": PaymentStatusSerializer(payment).data if payment else None,
        }
        return success_response(data=data)
