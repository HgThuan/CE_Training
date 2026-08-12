import json
import uuid
from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import UserFactory
from apps.ai.models import AIContentCache, AIRequestLog
from apps.ai.providers import AIProviderError, BaseAIProvider, ProviderResponse
from apps.ai.services import AIService
from apps.catalog.tests.factories import CategoryFactory
from apps.common.exceptions import BusinessError
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolate_ai_throttle_cache():
    cache.clear()
    yield
    cache.clear()


def provider_mock(*responses: dict) -> Mock:
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"
    provider.generate_text.side_effect = [
        ProviderResponse(text=json.dumps(response, ensure_ascii=False))
        for response in responses
    ]
    return provider


def approved_products(count: int) -> list[Product]:
    category = CategoryFactory()
    return [
        ProductFactory(
            status=Product.Status.APPROVED,
            category=category,
            name=f"Sản phẩm {index}",
            min_price=100_000 + index,
            max_price=150_000 + index,
        )
        for index in range(count)
    ]


def compare_response(product_count: int) -> dict:
    return {
        "rows": [
            {
                "label": "Điểm nổi bật",
                "values": [f"Giá trị {index}" for index in range(product_count)],
            }
        ],
        "recommendations": [
            {"need": "Tiết kiệm", "product_index": 0, "reason": "Giá phù hợp"}
        ],
    }


@pytest.mark.parametrize("product_count", [2, 3, 4])
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_compare_products_supports_two_to_four_public_products(product_count):
    products = approved_products(product_count)
    provider = provider_mock(compare_response(product_count))

    data = AIService(provider=provider).compare_products([item.pk for item in products])

    assert len(data["products"]) == product_count
    assert len(data["rows"][0]["values"]) == product_count
    assert data["recommendations"][0]["product_index"] == 0
    assert data["is_comparable"] is True
    assert data["compatibility_message"] is None
    assert data["is_ai_generated"] is True
    assert data["ai_label"] == "Tạo bởi AI"
    assert AIRequestLog.objects.get().feature == AIRequestLog.Feature.PRODUCT_COMPARE


@pytest.mark.parametrize("product_count", [1, 5])
def test_compare_products_rejects_invalid_cardinality(product_count):
    products = approved_products(product_count)

    with pytest.raises(BusinessError) as error:
        AIService().compare_products([item.pk for item in products])

    assert error.value.http_status == 400


def test_compare_products_rejects_missing_or_hidden_product():
    public = approved_products(1)[0]
    hidden = ProductFactory(status=Product.Status.HIDDEN)

    with pytest.raises(BusinessError) as error:
        AIService().compare_products([public.pk, hidden.pk])

    assert error.value.http_status == 404


def test_compare_products_returns_explanation_for_unrelated_category_groups():
    electronics = CategoryFactory(name="Điện tử")
    fashion = CategoryFactory(name="Thời trang")
    phone = ProductFactory(status=Product.Status.APPROVED, category=electronics)
    shirt = ProductFactory(status=Product.Status.APPROVED, category=fashion)
    provider = provider_mock(compare_response(2))

    data = AIService(provider=provider).compare_products([phone.pk, shirt.pk])

    assert data["is_comparable"] is False
    assert data["rows"] == []
    assert data["recommendations"] == []
    assert data["is_ai_generated"] is False
    assert data["ai_label"] is None
    assert "Điện tử" in data["compatibility_message"]
    assert "Thời trang" in data["compatibility_message"]
    provider.generate_text.assert_not_called()
    assert AIRequestLog.objects.count() == 0
    assert AIContentCache.objects.count() == 0


@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_compare_products_allows_sibling_categories_under_same_root():
    electronics = CategoryFactory(name="Điện tử")
    phones = CategoryFactory(name="Điện thoại", parent=electronics)
    tablets = CategoryFactory(name="Máy tính bảng", parent=electronics)
    products = [
        ProductFactory(status=Product.Status.APPROVED, category=phones),
        ProductFactory(status=Product.Status.APPROVED, category=tablets),
    ]
    provider = provider_mock(compare_response(2))

    data = AIService(provider=provider).compare_products(
        [product.pk for product in products]
    )

    assert data["is_comparable"] is True
    provider.generate_text.assert_called_once()


@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_compare_products_cache_is_order_independent():
    products = approved_products(2)
    provider = provider_mock(compare_response(2))
    service = AIService(provider=provider)

    first = service.compare_products([products[0].pk, products[1].pk])
    second = service.compare_products([products[1].pk, products[0].pk])

    assert second == first
    provider.generate_text.assert_called_once()
    assert AIRequestLog.objects.count() == 1
    assert AIContentCache.objects.filter(feature=AIRequestLog.Feature.PRODUCT_COMPARE).count() == 1


@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_compare_products_uses_rule_based_fallback_when_provider_fails():
    products = approved_products(2)
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"
    provider.generate_text.side_effect = AIProviderError(
        "unavailable", code="provider_unavailable", retryable=False
    )

    data = AIService(provider=provider).compare_products([item.pk for item in products])

    assert data["rows"]
    assert data["recommendations"] == []
    assert data["is_comparable"] is True
    assert data["is_ai_generated"] is False
    assert data["ai_label"] is None


@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_generate_listing_returns_plain_text_ai_content():
    provider = provider_mock(
        {
            "title": "<strong>Áo khoác nhẹ</strong>",
            "description": "<p>Thoáng khí.</p><script>alert('x')</script><p>Dễ phối đồ.</p>",
            "meta_description": "<em>Áo khoác cho ngày năng động.</em>",
        }
    )

    data = AIService(provider=provider).generate_product_listing(
        name="Áo khoác", keywords=["thoáng khí", "nhẹ"]
    )

    assert data["title"] == "Áo khoác nhẹ"
    assert "<" not in data["description"]
    assert "alert" not in data["description"]
    assert data["meta_description"] == "Áo khoác cho ngày năng động."
    assert data["is_ai_generated"] is True
    assert data["ai_label"] == "Tạo bởi AI — vui lòng kiểm tra lại trước khi lưu"
    assert AIRequestLog.objects.get().feature == AIRequestLog.Feature.SELLER_LISTING


@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_generate_listing_raises_clear_error_when_provider_fails():
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"
    provider.generate_text.side_effect = AIProviderError(
        "unavailable", code="provider_unavailable", retryable=False
    )

    with pytest.raises(BusinessError) as error:
        AIService(provider=provider).generate_product_listing(name="Áo khoác", keywords=[])

    assert error.value.http_status == 503
    assert "thử lại" in str(error.value)


def test_generate_listing_requires_a_product_name():
    with pytest.raises(BusinessError) as error:
        AIService().generate_product_listing(name="   ", keywords=[])

    assert error.value.http_status == 400
    assert str(error.value) == "Cần nhập tên sản phẩm trước khi tạo mô tả"


@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_generate_listing_never_caches_regeneration():
    provider = provider_mock(
        {"title": "Tiêu đề một", "description": "Mô tả một", "meta_description": "Meta một"},
        {"title": "Tiêu đề hai", "description": "Mô tả hai", "meta_description": "Meta hai"},
    )
    service = AIService(provider=provider)

    first = service.generate_product_listing(name="Sản phẩm", keywords=["bền"])
    second = service.generate_product_listing(name="Sản phẩm", keywords=["bền"])

    assert first["title"] != second["title"]
    assert provider.generate_text.call_count == 2
    assert AIRequestLog.objects.filter(feature=AIRequestLog.Feature.SELLER_LISTING).count() == 2
    assert AIContentCache.objects.filter(feature=AIRequestLog.Feature.SELLER_LISTING).count() == 0


def test_compare_endpoint_rejects_invalid_product_count():
    response = APIClient().post(
        reverse("product-compare"),
        {"product_ids": [str(uuid.uuid4())]},
        format="json",
    )
    assert response.status_code == 400


def test_listing_endpoint_is_seller_only():
    client = APIClient()
    client.force_authenticate(UserFactory(role=User.Role.CUSTOMER))
    response = client.post(
        reverse("seller-product-generate-listing"),
        {"name": "Sản phẩm", "keywords": []},
        format="json",
    )
    assert response.status_code == 403


def test_compare_endpoint_has_its_own_throttle():
    rates = {
        **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "ai_product_compare": "1/minute",
    }
    rest_framework = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates}
    payload = {
        "products": [], "rows": [], "recommendations": [],
        "is_comparable": True, "compatibility_message": None,
        "is_ai_generated": False, "ai_label": None,
    }
    request_body = {"product_ids": [str(uuid.uuid4()), str(uuid.uuid4())]}

    with (
        override_settings(REST_FRAMEWORK=rest_framework),
        patch("apps.ai.views.AIService.compare_products", return_value=payload) as compare,
    ):
        client = APIClient()
        first = client.post(reverse("product-compare"), request_body, format="json")
        second = client.post(reverse("product-compare"), request_body, format="json")
        assert first.status_code == 200
        assert second.status_code == 429
    assert compare.call_count == 1


def test_listing_endpoint_has_its_own_user_throttle():
    rates = {
        **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "ai_seller_listing": "1/minute",
    }
    rest_framework = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates}
    payload = {
        "title": "Tiêu đề", "description": "Mô tả", "meta_description": "Meta",
        "is_ai_generated": True,
        "ai_label": "Tạo bởi AI — vui lòng kiểm tra lại trước khi lưu",
    }

    with (
        override_settings(REST_FRAMEWORK=rest_framework),
        patch("apps.ai.views.AIService.generate_product_listing", return_value=payload) as generate,
    ):
        client = APIClient()
        client.force_authenticate(UserFactory(role=User.Role.SELLER))
        url = reverse("seller-product-generate-listing")
        assert client.post(url, {"name": "Tên"}, format="json").status_code == 200
        assert client.post(url, {"name": "Tên"}, format="json").status_code == 429
    assert generate.call_count == 1
