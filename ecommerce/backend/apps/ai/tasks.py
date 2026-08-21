from collections import Counter, defaultdict
from itertools import combinations

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from apps.product.selectors import ProductSelector

from .embedding_service import EmbeddingService
from .models import RecommendationEvent, RecommendationProfile


@shared_task(
    name="ai.index_product_embedding",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def index_product_embedding(product_id: str) -> dict:
    return EmbeddingService.index_product(product_id).as_dict()


# Backward-compatible plural import for the name used in the Sprint plan.
index_product_embeddings = index_product_embedding


@shared_task(
    name="ai.reindex_all_products",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def reindex_all_products(batch_size: int = 100) -> dict:
    if not EmbeddingService.is_enabled():
        return {"status": "disabled", "enqueued": 0}
    safe_batch_size = min(max(int(batch_size), 1), 1_000)
    product_ids = (
        ProductSelector.public_base()
        .order_by("pk")
        .values_list("pk", flat=True)
        .iterator(chunk_size=safe_batch_size)
    )
    enqueued = 0
    for product_id in product_ids:
        index_product_embedding.delay(str(product_id))
        enqueued += 1
    return {"status": "queued", "enqueued": enqueued}


@shared_task(name="ai.rebuild_recommendation_profiles")
def rebuild_recommendation_profiles() -> dict:
    """Build purchase co-occurrence profiles off the request path."""
    from apps.order.models import Order, OrderItem, ShopOrder
    from apps.product.models import Product

    rows = OrderItem.objects.exclude(product_id=None).filter(
        Q(shop_order__order__payment_status=Order.PaymentStatus.PAID)
        | Q(
            shop_order__fulfillment_status__in=(
                ShopOrder.FulfillmentStatus.DELIVERED,
                ShopOrder.FulfillmentStatus.COMPLETED,
            )
        )
    ).values_list(
        "shop_order__order__customer__user_id",
        "product_id",
        "quantity",
    )
    purchases: dict[object, Counter] = defaultdict(Counter)
    for user_id, product_id, quantity in rows.iterator(chunk_size=2_000):
        purchases[user_id][product_id] += max(1, int(quantity or 1))

    cooccurrence: dict[object, Counter] = defaultdict(Counter)
    for product_counts in purchases.values():
        for left, right in combinations(sorted(product_counts, key=str), 2):
            strength = min(product_counts[left], product_counts[right])
            cooccurrence[left][right] += strength
            cooccurrence[right][left] += strength

    all_product_ids = {product_id for counts in purchases.values() for product_id in counts}
    product_meta = {
        product_id: (category_id, brand_id)
        for product_id, category_id, brand_id in Product.objects.filter(
            pk__in=all_product_ids
        ).values_list("pk", "category_id", "brand_id")
    }
    generated_at = timezone.now()
    updated = 0
    RecommendationProfile.objects.exclude(user_id__in=purchases).delete()
    for user_id, product_counts in purchases.items():
        category_weights: Counter[str] = Counter()
        brand_weights: Counter[str] = Counter()
        related_scores: Counter = Counter()
        for product_id, weight in product_counts.items():
            meta = product_meta.get(product_id)
            if meta:
                category_id, brand_id = meta
                category_weights[str(category_id)] += weight
                if brand_id:
                    brand_weights[str(brand_id)] += weight
            for related_id, score in cooccurrence[product_id].items():
                if related_id not in product_counts:
                    related_scores[related_id] += weight * score
        related_ids = [
            str(product_id)
            for product_id, _score in sorted(
                related_scores.items(), key=lambda item: (-item[1], str(item[0]))
            )[:100]
        ]
        RecommendationProfile.objects.update_or_create(
            user_id=user_id,
            defaults={
                "category_weights": dict(category_weights),
                "brand_weights": dict(brand_weights),
                "related_product_ids": related_ids,
                "model_name": "purchase-cooccurrence-v1",
                "generated_at": generated_at,
            },
        )
        updated += 1
    return {"status": "rebuilt", "profiles": updated, "users": len(purchases)}


@shared_task(name="ai.record_purchase_recommendation_feedback")
def record_purchase_recommendation_feedback(order_id: str) -> dict:
    """Attribute a verified order to recent recommendation interactions."""
    from datetime import timedelta

    from apps.order.models import OrderItem

    items = list(
        OrderItem.objects.filter(shop_order__order_id=order_id, product_id__isnull=False)
        .values_list("shop_order__order__customer__user_id", "product_id")
        .distinct()
    )
    created = 0
    cutoff = timezone.now() - timedelta(days=30)
    for user_id, product_id in items:
        sources = RecommendationEvent.objects.filter(
            user_id=user_id,
            product_id=product_id,
            event_type__in=(
                RecommendationEvent.EventType.CLICK,
                RecommendationEvent.EventType.ADD_TO_CART,
            ),
            created_at__gte=cutoff,
        ).order_by("-created_at")[:10]
        for source in sources:
            _event, was_created = RecommendationEvent.objects.get_or_create(
                recommendation_id=source.recommendation_id,
                user_id=user_id,
                product_id=product_id,
                event_type=RecommendationEvent.EventType.PURCHASE,
                defaults={
                    "source": source.source,
                    "context": {"order_id": str(order_id), "attributed_event": str(source.pk)},
                },
            )
            created += int(was_created)
    return {"status": "recorded", "events": created}
