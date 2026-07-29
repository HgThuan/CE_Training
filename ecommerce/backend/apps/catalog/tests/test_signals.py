import pytest
from django.core.cache import cache

from apps.catalog.models import Category
from apps.common.cache_utils import CATEGORY_TREE_CACHE_KEY, HOME_PAGE_CACHE_KEY


@pytest.mark.django_db
def test_category_invalidation_runs_only_after_commit(django_capture_on_commit_callbacks):
    cache.set(CATEGORY_TREE_CACHE_KEY, ["cached-category"], timeout=60)
    cache.set(HOME_PAGE_CACHE_KEY, {"cached": True}, timeout=60)

    with django_capture_on_commit_callbacks(execute=True):
        Category.objects.create(name="Điện tử", slug="dien-tu")
        assert cache.get(CATEGORY_TREE_CACHE_KEY) == ["cached-category"]
        assert cache.get(HOME_PAGE_CACHE_KEY) == {"cached": True}

    assert cache.get(CATEGORY_TREE_CACHE_KEY) is None
    assert cache.get(HOME_PAGE_CACHE_KEY) is None
