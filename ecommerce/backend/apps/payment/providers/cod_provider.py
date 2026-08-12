from apps.common.exceptions import BusinessError

from .base import PaymentProvider, RefundResult


class CODProvider(PaymentProvider):
    def create_payment_url(self, order, transaction_ref: str) -> str:
        return ""

    def verify_callback(self, raw_payload: dict):
        raise BusinessError("COD không hỗ trợ payment callback")

    def create_refund(self, payment, refund) -> RefundResult:
        return RefundResult(successful=True, provider_reference=f"COD-{refund.refund_code}")
