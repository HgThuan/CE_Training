from django.db import IntegrityError, transaction

from apps.account.models import User
from apps.common.exceptions import BusinessError
from apps.product.models import Product

from .models import ProductAnswer, ProductQuestion

MAX_QA_CONTENT_LENGTH = 2000
MIN_QA_CONTENT_LENGTH = 3


def _validate_actor(user, *, role: str, message: str) -> None:
    if not (
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and not getattr(user, "is_deleted", True)
        and getattr(user, "role", None) == role
    ):
        raise BusinessError(message, http_status=403)


def _normalize_content(content: str) -> str:
    normalized = str(content).strip()
    if not MIN_QA_CONTENT_LENGTH <= len(normalized) <= MAX_QA_CONTENT_LENGTH:
        raise BusinessError(
            "Nội dung hỏi đáp không hợp lệ",
            errors={
                "content": [
                    f"Nội dung phải có từ {MIN_QA_CONTENT_LENGTH} đến {MAX_QA_CONTENT_LENGTH} ký tự"
                ]
            },
        )
    return normalized


class QuestionService:
    @staticmethod
    def create(*, customer, product: Product, content: str) -> ProductQuestion:
        _validate_actor(
            customer,
            role=User.Role.CUSTOMER,
            message="Chỉ Customer đang hoạt động mới có thể đặt câu hỏi",
        )
        return ProductQuestion.objects.create(
            product=product,
            customer=customer,
            content=_normalize_content(content),
        )


class AnswerService:
    @staticmethod
    @transaction.atomic
    def create(*, seller_user, question_id, content: str) -> ProductAnswer:
        _validate_actor(
            seller_user,
            role=User.Role.SELLER,
            message="Chỉ Seller đang hoạt động mới có thể trả lời câu hỏi",
        )
        question = (
            ProductQuestion.objects.select_for_update()
            .select_related("product__shop")
            .filter(
                pk=question_id,
                status=ProductQuestion.Status.VISIBLE,
                product__is_deleted=False,
                product__shop__is_deleted=False,
            )
            .first()
        )
        if question is None:
            raise BusinessError("Không tìm thấy câu hỏi", http_status=404)
        if question.product.shop.owner_id != seller_user.pk:
            raise BusinessError(
                "Bạn chỉ có thể trả lời câu hỏi của sản phẩm thuộc gian hàng mình",
                http_status=403,
            )
        if ProductAnswer.objects.filter(question=question).exists():
            raise BusinessError("Câu hỏi đã được trả lời", http_status=409)
        try:
            return ProductAnswer.objects.create(
                question=question,
                seller_user=seller_user,
                content=_normalize_content(content),
            )
        except IntegrityError as exc:
            raise BusinessError("Câu hỏi đã được trả lời", http_status=409) from exc
