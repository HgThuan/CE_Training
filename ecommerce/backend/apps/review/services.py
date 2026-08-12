from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.utils import timezone

from apps.common.exceptions import BusinessError
from apps.order.models import OrderItem, ShopOrder
from apps.product.models import Product

from .models import Review, ReviewMedia, ReviewReply, ReviewReport


class ReviewService:
    EDIT_WINDOW_DAYS = 7

    @classmethod
    @transaction.atomic
    def create(cls, *, order_item: OrderItem, user, rating: int, content="", media=()):
        item = (
            OrderItem.objects.select_for_update()
            .select_related("shop_order__order__customer__user")
            .get(pk=order_item.pk)
        )
        if item.shop_order.order.customer.user_id != user.pk:
            raise BusinessError("Bạn không có quyền đánh giá sản phẩm này", http_status=404)
        if item.shop_order.fulfillment_status != ShopOrder.FulfillmentStatus.COMPLETED:
            raise BusinessError("Chỉ có thể đánh giá sau khi đơn hoàn thành", http_status=409)
        if item.product_id is None:
            raise BusinessError("Sản phẩm không còn tồn tại", http_status=409)
        try:
            review = Review.objects.create(
                order_item=item,
                product_id=item.product_id,
                user=user,
                rating=rating,
                content=content,
                editable_until=timezone.now() + timedelta(days=cls.EDIT_WINDOW_DAYS),
            )
        except IntegrityError as exc:
            raise BusinessError("Sản phẩm trong đơn này đã được đánh giá", http_status=409) from exc
        cls._replace_media(review, media)
        cls.refresh_product_rating(review.product_id)
        return review

    @classmethod
    @transaction.atomic
    def update(cls, review: Review, *, user, rating: int, content="", media=None):
        locked = Review.objects.select_for_update().get(pk=review.pk)
        if locked.user_id != user.pk or locked.is_deleted:
            raise BusinessError("Không tìm thấy đánh giá", http_status=404)
        if locked.editable_until is None or timezone.now() > locked.editable_until:
            raise BusinessError("Đã hết thời hạn sửa đánh giá 7 ngày", http_status=409)
        locked.rating = rating
        locked.content = content
        locked.save(update_fields=("rating", "content", "updated_at"))
        if media is not None:
            cls._replace_media(locked, media)
        cls.refresh_product_rating(locked.product_id)
        return locked

    @staticmethod
    def _replace_media(review, media):
        ReviewMedia.objects.filter(review=review).delete()
        ReviewMedia.objects.bulk_create(
            [
                ReviewMedia(review=review, sort_order=index, **item)
                for index, item in enumerate(media)
            ]
        )

    @staticmethod
    def refresh_product_rating(product_id):
        stats = Review.objects.filter(
            product_id=product_id, status=Review.Status.VISIBLE, is_deleted=False
        ).aggregate(average=Avg("rating"), count=Count("id"))
        Product.objects.filter(pk=product_id).update(
            rating_average=Decimal(str(stats["average"] or 0)).quantize(Decimal("0.01")),
            rating_count=stats["count"],
        )

    @staticmethod
    @transaction.atomic
    def reply(review: Review, *, seller, content: str):
        if review.product.shop.owner_id != seller.pk:
            raise BusinessError("Không tìm thấy đánh giá", http_status=404)
        reply, _ = ReviewReply.objects.update_or_create(
            review=review, defaults={"seller_user": seller, "content": content}
        )
        return reply

    @staticmethod
    def report(review: Review, *, seller, reason_code: str, reason_detail=""):
        if review.product.shop.owner_id != seller.pk:
            raise BusinessError("Không tìm thấy đánh giá", http_status=404)
        try:
            return ReviewReport.objects.create(
                review=review,
                reported_by=seller,
                reason_code=reason_code,
                reason_detail=reason_detail,
            )
        except IntegrityError as exc:
            raise BusinessError(
                "Đánh giá này đã có báo cáo đang chờ xử lý", http_status=409
            ) from exc

    @classmethod
    @transaction.atomic
    def resolve_report(cls, report: ReviewReport, *, admin, action: str, note=""):
        locked = ReviewReport.objects.select_for_update().select_related("review").get(pk=report.pk)
        if locked.status != ReviewReport.Status.OPEN:
            raise BusinessError("Báo cáo đã được xử lý", http_status=409)
        locked.status = (
            ReviewReport.Status.RESOLVED if action == "HIDE" else ReviewReport.Status.REJECTED
        )
        locked.resolved_by = admin
        locked.resolution_note = note
        locked.save(update_fields=("status", "resolved_by", "resolution_note", "updated_at"))
        if action == "HIDE":
            locked.review.status = Review.Status.HIDDEN
            locked.review.save(update_fields=("status", "updated_at"))
            cls.refresh_product_rating(locked.review.product_id)
        return locked
