from celery import shared_task

from apps.product.selectors import ProductSelector

from .embedding_service import EmbeddingService


@shared_task(name="ai.index_product_embedding")
def index_product_embedding(product_id: str) -> dict:
    return EmbeddingService.index_product(product_id).as_dict()


# Backward-compatible plural import for the name used in the Sprint plan.
index_product_embeddings = index_product_embedding


@shared_task(name="ai.reindex_all_products")
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
