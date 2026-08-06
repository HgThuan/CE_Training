import re
from unittest.mock import patch

from django.http import QueryDict

from apps.common.cache_utils import (
    CACHE_KEY_VERSION,
    canonical_sha256,
    product_detail_cache_key,
    safe_cache_delete,
    safe_cache_delete_many,
    safe_cache_get,
    safe_cache_set,
    search_results_cache_key,
    search_suggestions_cache_key,
)


def test_canonical_sha256_is_stable_for_mapping_and_querydict_order():
    first = {
        "brand_id": "brand-1",
        "filters": {"in_stock": True, "price": [100_000, 500_000]},
        "page": 2,
        "q": "điện thoại",
    }
    second = {
        "q": "điện thoại",
        "page": 2,
        "filters": {"price": [100_000, 500_000], "in_stock": True},
        "brand_id": "brand-1",
    }
    first_querydict = QueryDict("q=phone&page=2&brand_id=brand-1")
    second_querydict = QueryDict("brand_id=brand-1&page=2&q=phone")

    assert canonical_sha256(first) == canonical_sha256(second)
    assert search_results_cache_key(first_querydict) == search_results_cache_key(second_querydict)


def test_dynamic_cache_keys_use_versioned_sha256_without_raw_input():
    search_key = search_results_cache_key({"q": "điện thoại dưới 5 triệu", "page": 1})
    product_key = product_detail_cache_key(
        slug="dien-thoai-pro",
        shop_slug="shop-viet",
    )

    assert re.fullmatch(rf"search:{CACHE_KEY_VERSION}:[0-9a-f]{{64}}", search_key)
    assert re.fullmatch(rf"product:{CACHE_KEY_VERSION}:[0-9a-f]{{64}}", product_key)
    assert "điện thoại" not in search_key
    assert "shop-viet" not in product_key


def test_suggestion_key_normalizes_case_whitespace_and_unicode():
    composed = "  ĐIỆN THOẠI  "
    decomposed = "điện thoại"

    assert search_suggestions_cache_key(composed) == search_suggestions_cache_key(decomposed)


def test_safe_cache_operations_degrade_when_backend_fails():
    with (
        patch(
            "apps.common.cache_utils.cache.get",
            side_effect=ConnectionError("cache unavailable"),
        ),
        patch(
            "apps.common.cache_utils.cache.set",
            side_effect=ConnectionError("cache unavailable"),
        ),
        patch(
            "apps.common.cache_utils.cache.delete",
            side_effect=ConnectionError("cache unavailable"),
        ),
        patch(
            "apps.common.cache_utils.cache.delete_many",
            side_effect=ConnectionError("cache unavailable"),
        ),
    ):
        assert safe_cache_get("missing", default={"fallback": True}) == {"fallback": True}
        assert safe_cache_set("key", {"value": 1}, timeout=60) is False
        assert safe_cache_delete("key") is False
        assert safe_cache_delete_many("key", "other") is False
