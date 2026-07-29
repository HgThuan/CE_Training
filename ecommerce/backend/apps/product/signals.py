from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.cache_utils import invalidate_product_cache_on_commit

from .models import (
    Product,
    ProductAttributeValue,
    ProductMedia,
    ProductVariant,
    VariantAttributeValue,
)


def _invalidate_product(product: Product) -> None:
    try:
        shop_slug = product.shop.slug
    except ObjectDoesNotExist:
        shop_slug = None
    invalidate_product_cache_on_commit(
        slug=product.slug,
        shop_slug=shop_slug,
    )


def _invalidate_product_id(product_id) -> None:
    product = (
        Product.objects.select_related("shop")
        .filter(pk=product_id)
        .only("slug", "shop__slug")
        .first()
    )
    if product is not None:
        _invalidate_product(product)


@receiver(
    (post_save, post_delete),
    sender=Product,
    dispatch_uid="product.invalidate_product_caches",
)
def invalidate_product_caches(instance: Product, **kwargs) -> None:
    _invalidate_product(instance)


@receiver(
    (post_save, post_delete),
    sender=ProductMedia,
    dispatch_uid="product.invalidate_media_product_caches",
)
def invalidate_media_product_caches(instance: ProductMedia, **kwargs) -> None:
    _invalidate_product_id(instance.product_id)


@receiver(
    (post_save, post_delete),
    sender=ProductVariant,
    dispatch_uid="product.invalidate_variant_product_caches",
)
def invalidate_variant_product_caches(instance: ProductVariant, **kwargs) -> None:
    _invalidate_product_id(instance.product_id)


@receiver(
    (post_save, post_delete),
    sender=ProductAttributeValue,
    dispatch_uid="product.invalidate_attribute_product_caches",
)
def invalidate_attribute_product_caches(instance: ProductAttributeValue, **kwargs) -> None:
    _invalidate_product_id(instance.product_id)


@receiver(
    (post_save, post_delete),
    sender=VariantAttributeValue,
    dispatch_uid="product.invalidate_variant_attribute_product_caches",
)
def invalidate_variant_attribute_product_caches(
    instance: VariantAttributeValue,
    **kwargs,
) -> None:
    product_id = (
        ProductVariant.objects.filter(pk=instance.variant_id)
        .values_list("product_id", flat=True)
        .first()
    )
    if product_id is not None:
        _invalidate_product_id(product_id)
