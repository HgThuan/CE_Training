from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.db.models import CharField
from django.urls import reverse

from apps.catalog.tests.factories import BrandFactory, CategoryFactory
from apps.inventory.models import InventoryBalance
from apps.product.models import Product
from apps.product.tests.factories import (
    ProductFactory,
    ProductMediaFactory,
    ProductVariantFactory,
)


@pytest.fixture(autouse=True)
def isolate_cache():
    cache.clear()
    yield
    cache.clear()


def test_postgres_trigram_lookup_is_registered():
    assert CharField().get_lookup("trigram_similar") is not None


@pytest.mark.django_db
def test_search_keyword_fallback_only_returns_public_products(api_client):
    visible = ProductFactory(
        status=Product.Status.APPROVED,
        name="Waterproof phone",
    )
    ProductFactory(
        status=Product.Status.DRAFT,
        name="Waterproof phone draft",
    )
    deleted = ProductFactory(
        status=Product.Status.APPROVED,
        name="Waterproof phone deleted",
        is_deleted=True,
    )

    response = api_client.get(
        reverse("product:search"),
        {"q": "waterproof"},
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert [item["id"] for item in response.data["data"]] == [str(visible.pk)]
    assert str(deleted.pk) not in {item["id"] for item in response.data["data"]}


@pytest.mark.django_db
def test_search_applies_whitelisted_filters_stock_and_sort(api_client):
    category = CategoryFactory(slug="dien-thoai")
    brand = BrandFactory(slug="future-tech")
    in_stock = ProductFactory(
        status=Product.Status.APPROVED,
        category=category,
        brand=brand,
        min_price=100_000,
        max_price=120_000,
        rating_average="4.80",
        sold_count=50,
    )
    in_stock_variant = ProductVariantFactory(
        product=in_stock,
        shop=in_stock.shop,
    )
    InventoryBalance.objects.create(
        variant=in_stock_variant,
        available_stock=5,
    )
    out_of_stock = ProductFactory(
        status=Product.Status.APPROVED,
        category=category,
        brand=brand,
        min_price=90_000,
        max_price=110_000,
        rating_average="4.90",
        sold_count=100,
    )
    out_variant = ProductVariantFactory(
        product=out_of_stock,
        shop=out_of_stock.shop,
    )
    InventoryBalance.objects.create(
        variant=out_variant,
        available_stock=0,
    )
    ProductFactory(
        status=Product.Status.APPROVED,
        category=CategoryFactory(),
        brand=brand,
        min_price=100_000,
        max_price=100_000,
        rating_average="5.00",
    )

    response = api_client.get(
        reverse("product:search"),
        {
            "category": str(category.pk),
            "brand": brand.slug,
            "price_min": "80000",
            "price_max": "130000",
            "rating_min": "4",
            "in_stock": "true",
            "shop": in_stock.shop.slug,
            "sort": "-sold_count",
        },
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.data["data"]] == [str(in_stock.pk)]


@pytest.mark.django_db
def test_search_rejects_unknown_query_parameters(api_client):
    response = api_client.get(
        reverse("product:search"),
        {"q": "phone", "unsafe_lookup": "shop__owner__email"},
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert "query_params" in response.data["errors"]


@pytest.mark.django_db
def test_search_reuses_cached_paginated_payload(api_client):
    ProductFactory(
        status=Product.Status.APPROVED,
        name="Cached laptop",
    )
    url = reverse("product:search")
    first_response = api_client.get(url, {"q": "laptop", "page_size": 5})

    assert first_response.status_code == 200
    with patch(
        "apps.product.views.SearchSelector.search",
        side_effect=AssertionError("search cache miss"),
    ):
        second_response = api_client.get(url, {"page_size": 5, "q": "laptop"})

    assert second_response.status_code == 200
    assert second_response.data == first_response.data


@pytest.mark.django_db
def test_suggestions_cache_top_ten_then_applies_requested_limit(api_client):
    for index in range(12):
        ProductFactory(
            status=Product.Status.APPROVED,
            name=f"Laptop {index:02d}",
        )
    url = reverse("product:search-suggestions")

    first_response = api_client.get(url, {"q": "Laptop", "limit": 3})

    assert first_response.status_code == 200
    assert len(first_response.data["data"]) == 3
    assert set(first_response.data["data"][0]) == {
        "id",
        "text",
        "slug",
        "shop_slug",
    }

    with patch(
        "apps.product.views.SearchSelector.suggestions",
        side_effect=AssertionError("suggestions cache miss"),
    ):
        second_response = api_client.get(url, {"q": " laptop ", "limit": 5})

    assert second_response.status_code == 200
    assert len(second_response.data["data"]) == 5


@pytest.mark.django_db
def test_product_detail_reuses_scoped_cached_data(api_client):
    product = ProductFactory(
        status=Product.Status.APPROVED,
        slug="cached-product",
    )
    ProductVariantFactory(product=product, shop=product.shop)
    ProductMediaFactory(product=product, is_primary=True)
    url = reverse(
        "product:public-product-detail",
        kwargs={"slug": product.slug},
    )

    first_response = api_client.get(url, {"shop_slug": product.shop.slug})

    assert first_response.status_code == 200
    with patch(
        "apps.product.views.ProductSelector.public_detail",
        side_effect=AssertionError("product detail cache miss"),
    ):
        second_response = api_client.get(url, {"shop_slug": product.shop.slug})

    assert second_response.status_code == 200
    assert second_response.data == first_response.data


@pytest.mark.django_db
def test_search_query_count_is_bounded(
    api_client,
    django_assert_max_num_queries,
):
    for index in range(6):
        product = ProductFactory(
            status=Product.Status.APPROVED,
            name=f"Optimized search product {index}",
        )
        ProductMediaFactory(product=product)

    with django_assert_max_num_queries(4):
        response = api_client.get(
            reverse("product:search"),
            {"q": "Optimized search", "page_size": 10},
        )

    assert response.status_code == 200
    assert len(response.data["data"]) == 6
