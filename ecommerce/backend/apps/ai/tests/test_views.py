from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.account.models import Shop, User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.catalog.tests.factories import BrandFactory, CategoryFactory
from apps.inventory.models import InventoryBalance
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory, ProductVariantFactory


@pytest.fixture(autouse=True)
def isolate_ai_throttle_cache():
    cache.clear()
    yield
    cache.clear()


def add_stock(product, quantity=5):
    variant = ProductVariantFactory(product=product, shop=product.shop)
    InventoryBalance.objects.create(
        variant=variant,
        available_stock=quantity,
    )


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True)
def test_smart_search_accepts_frontend_filter_contract_and_returns_standard_shape():
    category = CategoryFactory(slug="phones")
    ignored_category = CategoryFactory(slug="ignored")
    brand = BrandFactory(slug="trusted-brand")
    shop = ShopFactory(slug="trusted-shop")
    product = ProductFactory(
        status=Product.Status.APPROVED,
        name="Waterproof phone",
        category=category,
        brand=brand,
        shop=shop,
        min_price=4_000_000,
        max_price=4_500_000,
        rating_average="4.70",
        sold_count=10,
    )
    add_stock(product)
    intent = {
        "keywords": ["Waterproof phone"],
        "filters": {"category": ignored_category.slug, "price_max": 1_000_000},
        "explanation": "Khớp nhu cầu chống nước.",
        "ai_used": True,
        "fallback_used": False,
    }

    with patch(
        "apps.ai.search_service.AIService.extract_search_intent",
        return_value=intent,
    ):
        response = APIClient().get(
            reverse("ai:smart-search"),
            {
                "q": "phone chống nước",
                "category": category.slug,
                "brand": brand.slug,
                "price_min": "3000000",
                "price_max": "5000000",
                "rating_min": "4",
                "in_stock": "true",
                "shop": shop.slug,
                "sort": "-sold_count",
                "page": 1,
                "page_size": 12,
            },
        )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["ai_used"] is True
    assert response.data["data"]["fallback_used"] is False
    assert response.data["data"]["intent"]["filters"]["category"] == category.slug
    assert [item["id"] for item in response.data["data"]["results"]] == [str(product.pk)]
    assert response.data["meta"] == {
        "page": 1,
        "page_size": 12,
        "total_items": 1,
        "total_pages": 1,
    }


@pytest.mark.django_db
def test_smart_search_is_public_and_rejects_unknown_query_parameters():
    client = APIClient()

    public_response = client.get(reverse("ai:smart-search"), {"q": "phone"})
    invalid_response = client.get(
        reverse("ai:smart-search"),
        {"q": "phone", "shop__owner__email": "private@example.com"},
    )

    assert public_response.status_code == 200
    assert invalid_response.status_code == 400
    assert "query_params" in invalid_response.data["errors"]


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True)
def test_semantic_search_sqlite_fallback_only_returns_public_in_stock_products():
    visible = ProductFactory(
        status=Product.Status.APPROVED,
        name="Semantic phone",
    )
    add_stock(visible, 3)
    out_of_stock = ProductFactory(
        status=Product.Status.APPROVED,
        name="Semantic phone out",
    )
    add_stock(out_of_stock, 0)
    draft = ProductFactory(
        status=Product.Status.DRAFT,
        name="Semantic phone draft",
    )
    add_stock(draft, 4)
    locked_shop_product = ProductFactory(
        status=Product.Status.APPROVED,
        name="Semantic phone locked",
        shop=ShopFactory(status=Shop.Status.LOCKED),
    )
    add_stock(locked_shop_product, 4)

    with patch(
        "apps.ai.search_service.AIService.get_embedding",
    ) as get_embedding:
        response = APIClient().get(
            reverse("ai:semantic-search"),
            {"q": "Semantic phone"},
        )

    assert response.status_code == 200
    assert response.data["data"]["ai_used"] is False
    assert response.data["data"]["fallback_used"] is True
    assert [item["id"] for item in response.data["data"]["results"]] == [str(visible.pk)]
    get_embedding.assert_not_called()


@pytest.mark.django_db
def test_ai_search_guest_and_authenticated_throttle_buckets_are_separate():
    rates = {
        **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "ai_anonymous": "2/minute",
        "ai_authenticated": "3/minute",
    }
    rest_framework = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": rates,
    }
    url = reverse("ai:smart-search")

    with override_settings(REST_FRAMEWORK=rest_framework):
        guest = APIClient()
        assert guest.get(url, {"q": "phone"}).status_code == 200
        assert guest.get(url, {"q": "phone"}).status_code == 200
        assert guest.get(url, {"q": "phone"}).status_code == 429

        customer = UserFactory(role=User.Role.CUSTOMER)
        authenticated = APIClient()
        authenticated.force_authenticate(customer)
        assert authenticated.get(url, {"q": "phone"}).status_code == 200
        assert authenticated.get(url, {"q": "phone"}).status_code == 200
        assert authenticated.get(url, {"q": "phone"}).status_code == 200
        assert authenticated.get(url, {"q": "phone"}).status_code == 429
