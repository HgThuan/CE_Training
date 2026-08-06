from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.catalog.services import CategoryService
from apps.common.cache_utils import CATEGORY_TREE_CACHE_KEY


@pytest.mark.django_db
def test_category_tree_api_reuses_cached_serialized_data(api_client):
    cache.clear()
    category = CategoryService.create(name="Điện tử")

    first_response = api_client.get(reverse("catalog:public-category-tree"))

    assert first_response.status_code == 200
    assert cache.get(CATEGORY_TREE_CACHE_KEY) is not None
    assert first_response.data["data"][0]["id"] == str(category.pk)

    with patch(
        "apps.catalog.views.CategorySelector.public_tree",
        side_effect=AssertionError("cache miss"),
    ):
        second_response = api_client.get(reverse("catalog:public-category-tree"))

    assert second_response.status_code == 200
    assert second_response.data == first_response.data
    cache.clear()
