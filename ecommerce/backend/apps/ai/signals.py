from functools import partial

from django.conf import settings
from django.db import DatabaseError, transaction
from django.db.models import QuerySet
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.catalog.models import Brand, Category
from apps.common.models import SiteSetting
from apps.product.models import (
    Attribute,
    AttributeValue,
    Product,
    ProductAttributeValue,
)
from apps.product.selectors import ProductSelector

from .db_capabilities import product_embedding_table_available
from .models import ProductEmbedding
from .search_service import AI_SEARCH_FEATURE_KEY
from .services import AIService
from .tasks import index_product_embedding

AI_RECOMMENDATION_FEATURE_KEY = "feature.ai_recommendation.enabled"
_SOURCE_CHANGED_ATTRIBUTE = "_ai_embedding_source_changed"
_PREVIOUS_PRODUCT_ID_ATTRIBUTE = "_ai_embedding_previous_product_id"


def _delete_product_embeddings(product_id) -> None:
    if not product_embedding_table_available():
        return
    ProductEmbedding.objects.filter(product_id=product_id).delete()


def _embedding_indexing_enabled() -> bool:
    if not settings.AI_FEATURES_ENABLED or not AIService.is_configured():
        return False
    try:
        search_enabled = SiteSetting.get_bool(
            AI_SEARCH_FEATURE_KEY,
            default=settings.AI_FEATURES_ENABLED,
        )
        recommendation_enabled = SiteSetting.get_bool(
            AI_RECOMMENDATION_FEATURE_KEY,
            default=settings.AI_FEATURES_ENABLED,
        )
        return search_enabled or recommendation_enabled
    except DatabaseError:
        return False


def _enqueue_public_product_embeddings(product_ids: tuple[str, ...]) -> None:
    """Enqueue only products that are still public when the transaction commits."""
    if not _embedding_indexing_enabled():
        return
    public_ids = (
        ProductSelector.public_base()
        .filter(pk__in=product_ids)
        .order_by()
        .values_list("pk", flat=True)
    )
    for product_id in public_ids:
        index_product_embedding.delay(str(product_id))


def _schedule_product_ids(product_ids) -> None:
    if not _embedding_indexing_enabled():
        return
    normalized_ids = tuple(
        dict.fromkeys(str(product_id) for product_id in product_ids if product_id)
    )
    if not normalized_ids:
        return
    transaction.on_commit(
        partial(_enqueue_public_product_embeddings, normalized_ids),
    )


def _schedule_products(products: QuerySet[Product]) -> None:
    product_ids = products.order_by().values_list("pk", flat=True).distinct()
    _schedule_product_ids(product_ids)


def _source_fields_changed(
    *,
    sender,
    instance,
    field_names: tuple[str, ...],
    update_fields,
    update_field_names: frozenset[str] | None = None,
) -> bool:
    if instance._state.adding or not instance.pk:
        return False
    watched_update_fields = update_field_names or frozenset(field_names)
    if update_fields is not None and watched_update_fields.isdisjoint(update_fields):
        return False
    previous = sender._default_manager.filter(pk=instance.pk).values(*field_names).first()
    return previous is not None and any(
        previous[field_name] != getattr(instance, field_name) for field_name in field_names
    )


@receiver(
    post_save,
    sender=Product,
    dispatch_uid="ai.index_product_embedding_on_change",
)
def schedule_product_embedding(
    instance: Product,
    created: bool,
    **kwargs,
) -> None:
    if instance.status != Product.Status.APPROVED or instance.is_deleted:
        if not created:
            transaction.on_commit(partial(_delete_product_embeddings, instance.pk))
        return
    _schedule_product_ids((instance.pk,))


@receiver(
    pre_save,
    sender=ProductAttributeValue,
    dispatch_uid="ai.capture_product_attribute_link_change",
)
def capture_product_attribute_link_change(
    instance: ProductAttributeValue,
    update_fields=None,
    **kwargs,
) -> None:
    setattr(instance, _PREVIOUS_PRODUCT_ID_ATTRIBUTE, None)
    if instance._state.adding or not instance.pk:
        setattr(instance, _SOURCE_CHANGED_ATTRIBUTE, True)
        return
    watched_fields = {
        "product",
        "product_id",
        "attribute_value",
        "attribute_value_id",
    }
    if update_fields is not None and watched_fields.isdisjoint(update_fields):
        setattr(instance, _SOURCE_CHANGED_ATTRIBUTE, False)
        return
    previous = (
        ProductAttributeValue.objects.filter(pk=instance.pk)
        .values("product_id", "attribute_value_id")
        .first()
    )
    if previous is None:
        setattr(instance, _SOURCE_CHANGED_ATTRIBUTE, True)
        return
    setattr(
        instance,
        _PREVIOUS_PRODUCT_ID_ATTRIBUTE,
        previous["product_id"],
    )
    setattr(
        instance,
        _SOURCE_CHANGED_ATTRIBUTE,
        previous["product_id"] != instance.product_id
        or previous["attribute_value_id"] != instance.attribute_value_id,
    )


@receiver(
    post_save,
    sender=ProductAttributeValue,
    dispatch_uid="ai.index_product_attribute_link_on_change",
)
def schedule_product_attribute_link_change(
    instance: ProductAttributeValue,
    created: bool,
    **kwargs,
) -> None:
    if not created and not getattr(instance, _SOURCE_CHANGED_ATTRIBUTE, False):
        return
    _schedule_product_ids(
        (
            getattr(instance, _PREVIOUS_PRODUCT_ID_ATTRIBUTE, None),
            instance.product_id,
        )
    )


@receiver(
    post_delete,
    sender=ProductAttributeValue,
    dispatch_uid="ai.index_product_attribute_link_on_delete",
)
def schedule_product_attribute_link_delete(
    instance: ProductAttributeValue,
    **kwargs,
) -> None:
    _schedule_product_ids((instance.product_id,))


@receiver(
    pre_save,
    sender=Category,
    dispatch_uid="ai.capture_category_embedding_source_change",
)
@receiver(
    pre_save,
    sender=Brand,
    dispatch_uid="ai.capture_brand_embedding_source_change",
)
@receiver(
    pre_save,
    sender=Attribute,
    dispatch_uid="ai.capture_attribute_embedding_source_change",
)
def capture_named_source_change(
    sender,
    instance,
    update_fields=None,
    **kwargs,
) -> None:
    setattr(
        instance,
        _SOURCE_CHANGED_ATTRIBUTE,
        _source_fields_changed(
            sender=sender,
            instance=instance,
            field_names=("name",),
            update_fields=update_fields,
        ),
    )


@receiver(
    post_save,
    sender=Category,
    dispatch_uid="ai.index_category_products_on_name_change",
)
def schedule_category_name_change(
    instance: Category,
    created: bool,
    **kwargs,
) -> None:
    if created or not getattr(instance, _SOURCE_CHANGED_ATTRIBUTE, False):
        return
    _schedule_products(Product.objects.filter(category_id=instance.pk))


@receiver(
    post_save,
    sender=Brand,
    dispatch_uid="ai.index_brand_products_on_name_change",
)
def schedule_brand_name_change(
    instance: Brand,
    created: bool,
    **kwargs,
) -> None:
    if created or not getattr(instance, _SOURCE_CHANGED_ATTRIBUTE, False):
        return
    _schedule_products(Product.objects.filter(brand_id=instance.pk))


@receiver(
    post_save,
    sender=Attribute,
    dispatch_uid="ai.index_attribute_products_on_name_change",
)
def schedule_attribute_name_change(
    instance: Attribute,
    created: bool,
    **kwargs,
) -> None:
    if created or not getattr(instance, _SOURCE_CHANGED_ATTRIBUTE, False):
        return
    _schedule_products(
        Product.objects.filter(
            product_attribute_links__attribute_value__attribute_id=instance.pk,
        )
    )


@receiver(
    pre_save,
    sender=AttributeValue,
    dispatch_uid="ai.capture_attribute_value_embedding_source_change",
)
def capture_attribute_value_source_change(
    instance: AttributeValue,
    update_fields=None,
    **kwargs,
) -> None:
    setattr(
        instance,
        _SOURCE_CHANGED_ATTRIBUTE,
        _source_fields_changed(
            sender=AttributeValue,
            instance=instance,
            field_names=("attribute_id", "value", "display_value"),
            update_fields=update_fields,
            update_field_names=frozenset(
                {
                    "attribute",
                    "attribute_id",
                    "value",
                    "display_value",
                }
            ),
        ),
    )


@receiver(
    post_save,
    sender=AttributeValue,
    dispatch_uid="ai.index_attribute_value_products_on_change",
)
def schedule_attribute_value_change(
    instance: AttributeValue,
    created: bool,
    **kwargs,
) -> None:
    if created or not getattr(instance, _SOURCE_CHANGED_ATTRIBUTE, False):
        return
    _schedule_products(
        Product.objects.filter(
            product_attribute_links__attribute_value_id=instance.pk,
        )
    )
