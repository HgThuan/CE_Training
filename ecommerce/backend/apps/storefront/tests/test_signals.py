import pytest
from django.core.cache import cache

from apps.common.cache_utils import HOME_PAGE_CACHE_KEY
from apps.storefront.models import Banner


@pytest.mark.django_db
def test_banner_invalidation_runs_only_after_commit(django_capture_on_commit_callbacks):
    cache.set(HOME_PAGE_CACHE_KEY, {"cached": True}, timeout=60)

    with django_capture_on_commit_callbacks(execute=True):
        Banner.objects.create(
            title="Khuyến mãi",
            image_url="https://cdn.example.com/banner.webp",
        )
        assert cache.get(HOME_PAGE_CACHE_KEY) == {"cached": True}

    assert cache.get(HOME_PAGE_CACHE_KEY) is None
