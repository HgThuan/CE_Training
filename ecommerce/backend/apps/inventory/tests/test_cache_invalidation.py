import pytest
from django.core.cache import cache
from django.db import transaction

from apps.catalog.services import CategoryService
from apps.common.cache_utils import (
    CATEGORY_TREE_CACHE_KEY,
    HOME_PAGE_CACHE_KEY,
    product_detail_cache_key,
)
from apps.inventory.models import InventoryBalance
from apps.inventory.services import StockService
from apps.product.services import MediaService
from apps.product.tests.factories import ProductMediaFactory
from apps.storefront.models import Banner
from apps.storefront.services import BannerService

pytestmark = pytest.mark.django_db


def _seed_product_cache(product) -> tuple[str, str]:
    unscoped_key = product_detail_cache_key(slug=product.slug)
    scoped_key = product_detail_cache_key(
        slug=product.slug,
        shop_slug=product.shop.slug,
    )
    cache.set(HOME_PAGE_CACHE_KEY, {"cached": True}, timeout=60)
    cache.set(unscoped_key, {"cached": True}, timeout=60)
    cache.set(scoped_key, {"cached": True}, timeout=60)
    return unscoped_key, scoped_key


def test_banner_reorder_invalidates_home_cache_after_commit(
    django_capture_on_commit_callbacks,
):
    first = Banner.objects.create(
        image_url="https://cdn.example.com/first.webp",
        sort_order=1,
    )
    second = Banner.objects.create(
        image_url="https://cdn.example.com/second.webp",
        sort_order=2,
    )
    cache.set(HOME_PAGE_CACHE_KEY, {"cached": True}, timeout=60)

    with django_capture_on_commit_callbacks(execute=True):
        BannerService.reorder(source_id=first.pk, target_id=second.pk)
        assert cache.get(HOME_PAGE_CACHE_KEY) == {"cached": True}

    assert cache.get(HOME_PAGE_CACHE_KEY) is None


def test_category_reorder_invalidates_tree_and_home_after_commit(
    django_capture_on_commit_callbacks,
):
    first = CategoryService.create(name="First cache category")
    second = CategoryService.create(name="Second cache category")
    cache.set(CATEGORY_TREE_CACHE_KEY, ["cached"], timeout=60)
    cache.set(HOME_PAGE_CACHE_KEY, {"cached": True}, timeout=60)

    with django_capture_on_commit_callbacks(execute=True):
        CategoryService.reorder(
            items=[
                {"id": first.pk, "sort_order": 2},
                {"id": second.pk, "sort_order": 1},
            ]
        )
        assert cache.get(CATEGORY_TREE_CACHE_KEY) == ["cached"]
        assert cache.get(HOME_PAGE_CACHE_KEY) == {"cached": True}

    assert cache.get(CATEGORY_TREE_CACHE_KEY) is None
    assert cache.get(HOME_PAGE_CACHE_KEY) is None


def test_media_reorder_invalidates_parent_product_after_commit(
    django_capture_on_commit_callbacks,
    variant_a,
):
    product = variant_a.product
    first = ProductMediaFactory(product=product, sort_order=1)
    second = ProductMediaFactory(product=product, sort_order=2)
    unscoped_key, scoped_key = _seed_product_cache(product)

    with django_capture_on_commit_callbacks(execute=True):
        MediaService.reorder_media(
            product=product,
            ordered_ids=[second.pk, first.pk],
            seller_user=product.shop.owner,
        )
        assert cache.get(unscoped_key) == {"cached": True}
        assert cache.get(scoped_key) == {"cached": True}

    assert cache.get(HOME_PAGE_CACHE_KEY) is None
    assert cache.get(unscoped_key) is None
    assert cache.get(scoped_key) is None


def test_available_stock_update_invalidates_product_after_commit(
    django_capture_on_commit_callbacks,
    customer,
    balance_a,
):
    product = balance_a.variant.product
    unscoped_key, scoped_key = _seed_product_cache(product)

    with django_capture_on_commit_callbacks(execute=True):
        StockService.reserve_stock(
            balance_a.variant,
            1,
            "ORDER-CACHE",
            customer,
        )
        assert cache.get(unscoped_key) == {"cached": True}
        assert cache.get(scoped_key) == {"cached": True}

    assert cache.get(HOME_PAGE_CACHE_KEY) is None
    assert cache.get(unscoped_key) is None
    assert cache.get(scoped_key) is None


def test_inventory_balance_save_invalidates_product_after_commit(
    django_capture_on_commit_callbacks,
    balance_a,
):
    product = balance_a.variant.product
    unscoped_key, scoped_key = _seed_product_cache(product)

    with django_capture_on_commit_callbacks(execute=True):
        balance_a.available_stock = 4
        balance_a.save(update_fields=("available_stock", "updated_at"))
        assert cache.get(unscoped_key) == {"cached": True}

    assert cache.get(HOME_PAGE_CACHE_KEY) is None
    assert cache.get(unscoped_key) is None
    assert cache.get(scoped_key) is None


def test_stock_cache_invalidation_is_discarded_on_rollback(
    django_capture_on_commit_callbacks,
    customer,
    balance_a,
):
    product = balance_a.variant.product
    unscoped_key, scoped_key = _seed_product_cache(product)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with pytest.raises(RuntimeError, match="rollback cache invalidation"):
            with transaction.atomic():
                StockService.reserve_stock(
                    balance_a.variant,
                    1,
                    "ORDER-ROLLBACK-CACHE",
                    customer,
                )
                raise RuntimeError("rollback cache invalidation")

    balance_a.refresh_from_db()
    assert callbacks == []
    assert balance_a.available_stock == 10
    assert cache.get(HOME_PAGE_CACHE_KEY) == {"cached": True}
    assert cache.get(unscoped_key) == {"cached": True}
    assert cache.get(scoped_key) == {"cached": True}


def test_missing_balance_bulk_create_invalidates_product_after_commit(
    django_capture_on_commit_callbacks,
    seller_a,
    variant_a,
):
    assert not InventoryBalance.objects.filter(variant=variant_a).exists()
    unscoped_key, scoped_key = _seed_product_cache(variant_a.product)

    with django_capture_on_commit_callbacks(execute=True):
        StockService.update_threshold(
            variant_id=variant_a.pk,
            user=seller_a,
            low_stock_threshold=3,
        )
        assert cache.get(unscoped_key) == {"cached": True}

    assert cache.get(HOME_PAGE_CACHE_KEY) is None
    assert cache.get(unscoped_key) is None
    assert cache.get(scoped_key) is None
