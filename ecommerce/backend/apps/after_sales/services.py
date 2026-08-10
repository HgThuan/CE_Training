from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.account.models import Notification
from apps.common.exceptions import BusinessError
from apps.common.models import AuditLog, SiteSetting
from apps.order.models import OrderItem, ShopOrder
from apps.payment.services import PaymentService

from .models import Dispute, DisputeEvidence, ReturnRequest, ReturnRequestItem, ReturnRequestMedia


class ReturnRequestService:
    DEFAULT_WINDOW_DAYS = 7

    @classmethod
    @transaction.atomic
    def create(
        cls, *, shop_order: ShopOrder, customer, reason_code, reason_detail, items, media=()
    ):
        locked = (
            ShopOrder.objects.select_for_update()
            .select_related("order__customer__user", "shop")
            .get(pk=shop_order.pk)
        )
        if locked.order.customer.user_id != customer.pk:
            raise BusinessError("Không tìm thấy đơn hàng", http_status=404)
        if locked.fulfillment_status != ShopOrder.FulfillmentStatus.COMPLETED:
            raise BusinessError(
                "Chỉ có thể yêu cầu trả hàng khi đơn đã hoàn thành", http_status=409
            )
        window_days = int(SiteSetting.get_value("returns.window_days", cls.DEFAULT_WINDOW_DAYS))
        completed_at = locked.completed_at or locked.updated_at
        if (timezone.now() - completed_at).days > window_days:
            raise BusinessError(f"Đã quá thời hạn trả hàng {window_days} ngày", http_status=409)
        if (
            ReturnRequest.objects.filter(shop_order=locked)
            .exclude(status=ReturnRequest.Status.CLOSED)
            .exists()
        ):
            raise BusinessError("Đơn của shop đã có yêu cầu trả hàng", http_status=409)

        order_items = {
            str(item.pk): item
            for item in OrderItem.objects.select_for_update().filter(shop_order=locked)
        }
        requested_ids = [str(item["order_item_id"]) for item in items]
        if len(set(requested_ids)) != len(requested_ids):
            raise BusinessError("Mỗi sản phẩm chỉ được chọn một lần")
        if any(item_id not in order_items for item_id in requested_ids):
            raise BusinessError("Sản phẩm không thuộc đơn hàng", http_status=400)

        request = ReturnRequest.objects.create(
            shop_order=locked,
            customer=customer,
            reason_code=reason_code,
            reason_detail=reason_detail,
        )
        request_items = []
        for payload in items:
            order_item = order_items[str(payload["order_item_id"])]
            quantity = payload["quantity"]
            if quantity > order_item.quantity:
                raise BusinessError("Số lượng trả vượt quá số lượng đã mua")
            amount = (
                order_item.line_total * Decimal(quantity) / Decimal(order_item.quantity)
            ).quantize(Decimal("1"))
            request_items.append(
                ReturnRequestItem(
                    return_request=request,
                    order_item=order_item,
                    quantity=quantity,
                    requested_refund_amount=amount,
                )
            )
        ReturnRequestItem.objects.bulk_create(request_items)
        ReturnRequestMedia.objects.bulk_create(
            [ReturnRequestMedia(return_request=request, **entry) for entry in media]
        )
        locked.fulfillment_status = ShopOrder.FulfillmentStatus.RETURN_REQUESTED
        locked.save(update_fields=("fulfillment_status", "updated_at"))
        return request

    @classmethod
    @transaction.atomic
    def seller_decide(cls, return_request: ReturnRequest, *, seller, action, response):
        locked = (
            ReturnRequest.objects.select_for_update()
            .select_related("shop_order__shop", "shop_order__order")
            .prefetch_related("items")
            .get(pk=return_request.pk)
        )
        if locked.shop_order.shop.owner_id != seller.pk:
            raise BusinessError("Không tìm thấy yêu cầu", http_status=404)
        if locked.status != ReturnRequest.Status.REQUESTED:
            raise BusinessError("Yêu cầu không còn chờ seller xử lý", http_status=409)
        locked.seller_response = response
        if action == "REJECT":
            locked.status = ReturnRequest.Status.SELLER_REJECTED
            locked.shop_order.fulfillment_status = ShopOrder.FulfillmentStatus.RETURN_REJECTED
            locked.shop_order.save(update_fields=("fulfillment_status", "updated_at"))
        else:
            locked.status = ReturnRequest.Status.REFUND_PENDING
            amount = locked.items.aggregate(total=Sum("requested_refund_amount"))[
                "total"
            ] or Decimal("0")
            locked.items.update(approved_refund_amount=F("requested_refund_amount"))
            refund = PaymentService.refund_amount(
                locked.shop_order,
                amount=amount,
                reason=f"Seller approved return {locked.pk}",
                idempotency_key=f"return:{locked.pk}:seller",
                return_request=locked,
            )
            if refund.status == refund.Status.SUCCEEDED:
                locked.status = ReturnRequest.Status.REFUNDED
                locked.resolved_at = timezone.now()
                locked.shop_order.fulfillment_status = ShopOrder.FulfillmentStatus.RETURNED
                locked.shop_order.save(update_fields=("fulfillment_status", "updated_at"))
        locked.save(update_fields=("status", "seller_response", "resolved_at", "updated_at"))
        return locked

    @staticmethod
    @transaction.atomic
    def escalate(return_request: ReturnRequest, *, customer):
        locked = (
            ReturnRequest.objects.select_for_update()
            .select_related("shop_order")
            .get(pk=return_request.pk)
        )
        if locked.customer_id != customer.pk:
            raise BusinessError("Không tìm thấy yêu cầu", http_status=404)
        if locked.status != ReturnRequest.Status.SELLER_REJECTED:
            raise BusinessError("Chỉ có thể khiếu nại sau khi seller từ chối", http_status=409)
        dispute, created = Dispute.objects.get_or_create(
            return_request=locked,
            defaults={"shop_order": locked.shop_order, "opened_by": customer},
        )
        if created:
            DisputeEvidence.objects.create(
                dispute=dispute, submitted_by=customer, content=locked.reason_detail
            )
        locked.status = ReturnRequest.Status.ESCALATED
        locked.save(update_fields=("status", "updated_at"))
        return dispute


class DisputeService:
    @staticmethod
    @transaction.atomic
    def start_review(dispute: Dispute, *, admin):
        locked = Dispute.objects.select_for_update().get(pk=dispute.pk)
        if locked.status == Dispute.Status.OPEN:
            locked.status = Dispute.Status.REVIEWING
            locked.assigned_admin = admin
            locked.save(update_fields=("status", "assigned_admin", "updated_at"))
        return locked

    @staticmethod
    @transaction.atomic
    def resolve(dispute: Dispute, *, admin, decision, note, refund_amount=None, request_id=""):
        locked = (
            Dispute.objects.select_for_update(of=("self",))
            .select_related(
                "return_request__customer",
                "return_request__shop_order__order",
                "shop_order__shop__owner",
            )
            .prefetch_related("return_request__items")
            .get(pk=dispute.pk)
        )
        if locked.status not in {Dispute.Status.OPEN, Dispute.Status.REVIEWING}:
            raise BusinessError("Tranh chấp đã được giải quyết", http_status=409)
        requested_total = locked.return_request.items.aggregate(
            total=Sum("requested_refund_amount")
        )["total"] or Decimal("0")
        amount = Decimal("0")
        if decision == Dispute.Decision.REFUND_FULL:
            amount = requested_total
        elif decision == Dispute.Decision.REFUND_PARTIAL:
            amount = refund_amount
            if amount is None or amount <= 0 or amount >= requested_total:
                raise BusinessError("Tiền hoàn một phần phải lớn hơn 0 và nhỏ hơn tổng yêu cầu")

        if amount:
            refund = PaymentService.refund_amount(
                locked.shop_order,
                amount=amount,
                reason=f"Admin dispute decision {locked.pk}: {note}",
                idempotency_key=f"dispute:{locked.pk}",
                return_request=locked.return_request,
            )
            locked.return_request.status = (
                ReturnRequest.Status.REFUNDED
                if refund.status == refund.Status.SUCCEEDED
                else ReturnRequest.Status.REFUND_PENDING
            )
        else:
            locked.return_request.status = ReturnRequest.Status.CLOSED
        locked.return_request.resolved_at = timezone.now()
        locked.return_request.save(update_fields=("status", "resolved_at", "updated_at"))
        locked.status = Dispute.Status.RESOLVED
        locked.decision = decision
        locked.decision_note = note
        locked.refund_amount = amount or None
        locked.assigned_admin = admin
        locked.resolved_at = timezone.now()
        locked.save(
            update_fields=(
                "status",
                "decision",
                "decision_note",
                "refund_amount",
                "assigned_admin",
                "resolved_at",
                "updated_at",
            )
        )
        AuditLog.objects.create(
            actor=admin,
            action="dispute.resolve",
            target_type="Dispute",
            target_id=str(locked.pk),
            reason=note,
            request_id=request_id,
            diff={"decision": decision, "refund_amount": str(amount)},
        )
        decision_label = locked.get_decision_display()
        message = (
            f"Tranh chấp cho đơn {locked.shop_order.shop_order_code} đã được giải quyết: "
            f"{decision_label}. Ghi chú của Admin: {note}"
        )
        notification_metadata = {
            "event": "dispute_resolved",
            "dispute_id": str(locked.pk),
            "order_id": str(locked.shop_order.order_id),
            "shop_order_id": str(locked.shop_order_id),
            "decision": decision,
            "refund_amount": str(amount),
        }
        Notification.objects.create(
            user=locked.return_request.customer,
            kind=Notification.Kind.ORDER,
            title="Admin đã giải quyết tranh chấp",
            message=message,
            metadata=notification_metadata,
        )
        Notification.objects.create(
            user=locked.shop_order.shop.owner,
            kind=Notification.Kind.ORDER,
            title="Admin đã giải quyết tranh chấp",
            message=message,
            metadata=notification_metadata,
        )
        return locked
