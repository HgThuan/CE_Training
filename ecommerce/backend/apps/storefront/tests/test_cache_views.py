from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.common.cache_utils import HOME_PAGE_CACHE_KEY
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory
from apps.storefront.models import Banner


@pytest.mark.django_db
def test_home_api_reuses_cached_serialized_data(api_client):
    cache.clear()
    Banner.objects.create(
        title="Khuyến mãi",
        image_url="https://cdn.example.com/banner.webp",
    )
    product = ProductFactory(status=Product.Status.APPROVED)

    first_response = api_client.get(reverse("storefront:home"))

    assert first_response.status_code == 200
    assert cache.get(HOME_PAGE_CACHE_KEY) is not None
    assert first_response.data["data"]["new_arrivals"][0]["id"] == str(product.pk)

    with patch(
        "apps.storefront.views.get_home_products",
        side_effect=AssertionError("cache miss"),
    ):
        second_response = api_client.get(reverse("storefront:home"))

    assert second_response.status_code == 200
    assert second_response.data == first_response.data
    cache.clear()
