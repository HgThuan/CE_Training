import pytest
from django.core.cache import cache

from apps.account.tests.factories import ShopFactory
from apps.catalog.tests.factories import CategoryFactory
from apps.common.cache_utils import (
    HOME_PAGE_CACHE_KEY,
    product_detail_cache_key,
)
from apps.product.tests.factories import ProductFactory, ProductMediaFactory


def _seed_product_cache(*, slug: str, shop_slug: str) -> tuple[str, str]:
    unscoped_key = product_detail_cache_key(slug=slug)
    scoped_key = product_detail_cache_key(slug=slug, shop_slug=shop_slug)
    cache.set(HOME_PAGE_CACHE_KEY, {"cached": True}, timeout=60)
    cache.set(unscoped_key, {"cached": True}, timeout=60)
    cache.set(scoped_key, {"cached": True}, timeout=60)
    return unscoped_key, scoped_key


@pytest.mark.django_db
def test_product_invalidation_runs_only_after_commit(django_capture_on_commit_callbacks):
    shop = ShopFactory(slug="shop-viet")
    category = CategoryFactory()
    unscoped_key, scoped_key = _seed_product_cache(
        slug="dien-thoai-pro",
        shop_slug=shop.slug,
    )

    with django_capture_on_commit_callbacks(execute=True):
        ProductFactory(
            shop=shop,
            category=category,
            slug="dien-thoai-pro",
        )
        assert cache.get(HOME_PAGE_CACHE_KEY) == {"cached": True}
        assert cache.get(unscoped_key) == {"cached": True}
        assert cache.get(scoped_key) == {"cached": True}

    assert cache.get(HOME_PAGE_CACHE_KEY) is None
    assert cache.get(unscoped_key) is None
    assert cache.get(scoped_key) is None


@pytest.mark.django_db
def test_product_media_change_invalidates_parent_product_cache(
    django_capture_on_commit_callbacks,
):
    product = ProductFactory(slug="laptop-ai")
    unscoped_key, scoped_key = _seed_product_cache(
        slug=product.slug,
        shop_slug=product.shop.slug,
    )

    with django_capture_on_commit_callbacks(execute=True):
        ProductMediaFactory(product=product)
        assert cache.get(unscoped_key) == {"cached": True}

    assert cache.get(HOME_PAGE_CACHE_KEY) is None
    assert cache.get(unscoped_key) is None
    assert cache.get(scoped_key) is None
