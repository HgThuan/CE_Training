import hashlib
import hmac
from decimal import Decimal
from urllib.parse import quote_plus, urlencode

from django.conf import settings

from apps.common.exceptions import BusinessError

from .base import PaymentCallbackResult, PaymentProvider, RefundResult


def _canonical_payload(payload: dict) -> str:
    values = {
        str(key): str(value)
        for key, value in payload.items()
        if value not in (None, "") and key not in {"vnp_SecureHash", "vnp_SecureHashType"}
    }
    return "&".join(f"{quote_plus(key)}={quote_plus(values[key])}" for key in sorted(values))


class VNPayProvider(PaymentProvider):
    def _signature(self, payload: dict) -> str:
        secret = settings.VNPAY_HASH_SECRET.encode("utf-8")
        return hmac.new(
            secret, _canonical_payload(payload).encode("utf-8"), hashlib.sha512
        ).hexdigest()

    def create_payment_url(self, order, transaction_ref: str) -> str:
        if not settings.VNPAY_TMN_CODE or not settings.VNPAY_HASH_SECRET:
            raise BusinessError("VNPay sandbox chưa được cấu hình", http_status=503)
        separator = "&" if "?" in settings.VNPAY_RETURN_URL else "?"
        return_url = f"{settings.VNPAY_RETURN_URL}{separator}order_id={order.pk}"
        payload = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": settings.VNPAY_TMN_CODE,
            "vnp_Amount": int(order.grand_total * 100),
            "vnp_CurrCode": order.currency,
            "vnp_TxnRef": transaction_ref,
            "vnp_OrderInfo": f"Thanh toan don {order.order_code}",
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": return_url,
            "vnp_CreateDate": order.placed_at.strftime("%Y%m%d%H%M%S"),
        }
        payload["vnp_SecureHash"] = self._signature(payload)
        return f"{settings.VNPAY_PAYMENT_URL}?{urlencode(payload)}"

    def verify_callback(self, raw_payload: dict) -> PaymentCallbackResult:
        supplied = str(raw_payload.get("vnp_SecureHash", "")).lower()
        if not supplied or not hmac.compare_digest(supplied, self._signature(raw_payload)):
            raise BusinessError("Chữ ký VNPay không hợp lệ", http_status=400)
        try:
            amount = Decimal(str(raw_payload["vnp_Amount"])) / Decimal("100")
            transaction_ref = str(raw_payload["vnp_TxnRef"])
        except (KeyError, ValueError) as exc:
            raise BusinessError("Payload VNPay không hợp lệ") from exc
        provider_transaction_id = str(raw_payload.get("vnp_TransactionNo") or "") or None
        event_id = str(
            raw_payload.get("vnp_TransactionNo") or raw_payload.get("vnp_BankTranNo") or ""
        )
        if not event_id:
            event_id = hashlib.sha256(_canonical_payload(raw_payload).encode()).hexdigest()
        code = str(raw_payload.get("vnp_ResponseCode", "99"))
        return PaymentCallbackResult(
            transaction_ref=transaction_ref,
            provider_event_id=event_id,
            provider_transaction_id=provider_transaction_id,
            amount=amount,
            currency=str(raw_payload.get("vnp_CurrCode", "VND")),
            successful=code == "00" and str(raw_payload.get("vnp_TransactionStatus", "00")) == "00",
            response_code=code,
        )

    def create_refund(self, payment, refund) -> RefundResult:
        # The sandbox refund API requires merchant-side mutual TLS in some environments.
        # Persisting the refund first keeps cancellation atomic; a retryable task processes it.
        return RefundResult(successful=False, error="VNPay refund endpoint chưa được cấu hình")
