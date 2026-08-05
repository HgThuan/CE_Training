from .models import Review, ReviewReport


def review_graph():
    return Review.objects.select_related(
        "user", "product", "order_item__shop_order__order", "reply__seller_user"
    ).prefetch_related("media")


def get_public_product_reviews(product_id):
    return review_graph().filter(
        product_id=product_id,
        status=Review.Status.VISIBLE,
        is_deleted=False,
    )


def get_reviews_for_seller(user, *, rating=None, status=None):
    queryset = review_graph().filter(product__shop__owner=user, is_deleted=False)
    if rating:
        queryset = queryset.filter(rating=rating)
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def get_open_review_reports():
    return (
        ReviewReport.objects.select_related(
            "reported_by",
            "review__user",
            "review__product",
            "review__order_item__shop_order__order",
        )
        .prefetch_related("review__media")
        .filter(status=ReviewReport.Status.OPEN)
    )
