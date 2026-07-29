from django.db.models import QuerySet

from apps.product.models import Product
from apps.product.selectors import ProductSelector

from .models import ProductQuestion


def get_public_product(product_id) -> Product | None:
    return ProductSelector.public_base().filter(pk=product_id).first()


def get_public_questions(*, product: Product) -> QuerySet[ProductQuestion]:
    return (
        ProductQuestion.objects.filter(
            product=product,
            status=ProductQuestion.Status.VISIBLE,
        )
        .select_related(
            "customer",
            "answer",
            "answer__seller_user",
        )
        .order_by("-created_at", "-id")
    )
