from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaymentCallbackResult:
    transaction_ref: str
    provider_event_id: str
    provider_transaction_id: str | None
    amount: Decimal
    currency: str
    successful: bool
    response_code: str


@dataclass(frozen=True)
class RefundResult:
    successful: bool
    provider_reference: str | None = None
    error: str | None = None


class PaymentProvider(ABC):
    @abstractmethod
    def create_payment_url(self, order, transaction_ref: str) -> str: ...

    @abstractmethod
    def verify_callback(self, raw_payload: dict) -> PaymentCallbackResult: ...

    @abstractmethod
    def create_refund(self, payment, refund) -> RefundResult: ...
