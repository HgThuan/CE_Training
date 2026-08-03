from celery import shared_task

from .models import Refund
from .services import PaymentService


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_refund(refund_id: str) -> str:
    refund = Refund.objects.select_related("payment").get(pk=refund_id)
    if refund.status != Refund.Status.PENDING:
        return refund.status
    return PaymentService.process_refund(refund).status
