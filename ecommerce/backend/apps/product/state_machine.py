import logging

from django.db import transaction

from apps.account.models import User
from apps.common.exceptions import BusinessError
from apps.common.models import AuditLog

from .models import Product, ProductVariant

logger = logging.getLogger(__name__)


class ProductStateMachine:
    """Central authority for every Product status transition."""

    TRANSITIONS = {
        Product.Status.DRAFT: {Product.Status.PENDING_REVIEW},
        Product.Status.PENDING_REVIEW: {
            Product.Status.APPROVED,
            Product.Status.REJECTED,
        },
        Product.Status.REJECTED: {Product.Status.DRAFT},
        Product.Status.APPROVED: {
            Product.Status.HIDDEN,
            Product.Status.SUSPENDED,
        },
        Product.Status.HIDDEN: {Product.Status.APPROVED},
        Product.Status.SUSPENDED: {Product.Status.APPROVED},
    }
    SELLER_TRANSITIONS = {
        (Product.Status.DRAFT, Product.Status.PENDING_REVIEW),
        (Product.Status.REJECTED, Product.Status.DRAFT),
        (Product.Status.APPROVED, Product.Status.SUSPENDED),
        (Product.Status.SUSPENDED, Product.Status.APPROVED),
    }
    ACTIONS = {
        (Product.Status.DRAFT, Product.Status.PENDING_REVIEW): "submit_product_review",
        (Product.Status.PENDING_REVIEW, Product.Status.APPROVED): "approve_product",
        (Product.Status.PENDING_REVIEW, Product.Status.REJECTED): "reject_product",
        (Product.Status.REJECTED, Product.Status.DRAFT): "revise_rejected_product",
        (Product.Status.APPROVED, Product.Status.HIDDEN): "hide_product",
        (Product.Status.HIDDEN, Product.Status.APPROVED): "unhide_product",
        (Product.Status.APPROVED, Product.Status.SUSPENDED): "suspend_product",
        (Product.Status.SUSPENDED, Product.Status.APPROVED): "restore_product",
    }
    DELETABLE_STATUSES = {Product.Status.DRAFT, Product.Status.HIDDEN}

    @classmethod
    def can_soft_delete(cls, product: Product) -> bool:
        return product.status in cls.DELETABLE_STATUSES

    @classmethod
    @transaction.atomic
    def transition(
        cls,
        product: Product,
        to_status: str,
        *,
        actor,
        note: str = "",
        request_id: str = "",
    ) -> Product:
        locked_product = (
            Product.objects.select_for_update()
            .select_related("shop")
            .filter(pk=product.pk, is_deleted=False)
            .first()
        )
        if locked_product is None:
            raise BusinessError("Không tìm thấy sản phẩm", http_status=404)

        from_status = locked_product.status
        normalized_status = str(to_status)
        if normalized_status not in cls.TRANSITIONS.get(from_status, set()):
            raise BusinessError(
                f"Không thể chuyển sản phẩm từ {from_status} sang {normalized_status}",
                errors={"status": ["Chuyển trạng thái không hợp lệ theo vòng đời sản phẩm"]},
            )

        if (
            normalized_status == Product.Status.APPROVED
            and not ProductVariant.objects.filter(
                product=locked_product,
                is_active=True,
                is_deleted=False,
            ).exists()
        ):
            raise BusinessError(
                "Không thể duyệt sản phẩm chưa có SKU khả dụng",
                errors={"variants": ["Sản phẩm phải có ít nhất một biến thể"]},
            )

        transition = (from_status, normalized_status)
        if transition in cls.SELLER_TRANSITIONS:
            if (
                getattr(actor, "role", None) != User.Role.SELLER
                or not actor.is_active
                or actor.is_deleted
                or locked_product.shop.owner_id != actor.pk
            ):
                raise BusinessError(
                    "Bạn không có quyền chuyển trạng thái sản phẩm này",
                    errors={"product": ["Sản phẩm không thuộc gian hàng của bạn"]},
                    http_status=403,
                )
        elif (
            getattr(actor, "role", None) != User.Role.ADMIN
            or not actor.is_active
            or actor.is_deleted
        ):
            raise BusinessError(
                "Chỉ Admin được thực hiện chuyển trạng thái này",
                errors={"role": ["Yêu cầu vai trò Admin"]},
                http_status=403,
            )

        normalized_note = note.strip()
        if (
            normalized_status
            in {
                Product.Status.REJECTED,
                Product.Status.HIDDEN,
            }
            and not normalized_note
        ):
            action_label = (
                "từ chối" if normalized_status == Product.Status.REJECTED else "ẩn sản phẩm"
            )
            raise BusinessError(
                f"Lý do {action_label} là bắt buộc",
                errors={"reason": [f"Vui lòng nhập lý do {action_label}"]},
            )

        locked_product.status = normalized_status
        update_fields = {"status", "updated_at"}
        if normalized_status in {
            Product.Status.REJECTED,
            Product.Status.HIDDEN,
        }:
            locked_product.rejection_reason = normalized_note
            update_fields.add("rejection_reason")
        elif normalized_status in {
            Product.Status.DRAFT,
            Product.Status.APPROVED,
        }:
            locked_product.rejection_reason = None
            update_fields.add("rejection_reason")
        locked_product.save(update_fields=update_fields)

        AuditLog.objects.create(
            actor=actor,
            action=cls.ACTIONS[transition],
            target_type="Product",
            target_id=str(locked_product.pk),
            reason=normalized_note,
            request_id=request_id,
            diff={
                "status": {
                    "before": from_status,
                    "after": normalized_status,
                }
            },
        )
        logger.info(
            "Product status transitioned",
            extra={
                "request_id": request_id,
                "user_id": actor.pk,
                "product_id": str(locked_product.pk),
                "from_status": from_status,
                "to_status": normalized_status,
            },
        )
        return locked_product
