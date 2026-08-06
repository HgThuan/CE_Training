import hashlib
import json
import logging
import unicodedata
from collections.abc import Mapping, Sequence, Set
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from functools import partial
from typing import Any
from uuid import UUID

from django.core.cache import cache
from django.db import transaction
from django.utils.datastructures import MultiValueDict

logger = logging.getLogger(__name__)

CACHE_KEY_VERSION = "v1"

HOME_PAGE_CACHE_TTL = 10 * 60
CATEGORY_TREE_CACHE_TTL = 60 * 60
SEARCH_RESULTS_CACHE_TTL = 5 * 60
PRODUCT_DETAIL_CACHE_TTL = 10 * 60
SEARCH_SUGGESTIONS_CACHE_TTL = 5 * 60

HOME_PAGE_CACHE_KEY = f"home:page:{CACHE_KEY_VERSION}"
CATEGORY_TREE_CACHE_KEY = f"categories:tree:{CACHE_KEY_VERSION}"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, MultiValueDict):
        return {
            str(key): _canonicalize(values)
            for key, values in sorted(value.lists(), key=lambda item: str(item[0]))
        }
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, Set) and not isinstance(value, (str, bytes, bytearray)):
        normalized = [_canonicalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise TypeError(f"Unsupported cache-key value: {type(value).__name__}")


def canonical_sha256(value: Any) -> str:
    serialized = json.dumps(
        _canonicalize(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def build_cache_key(namespace: str, payload: Any) -> str:
    normalized_namespace = namespace.strip().strip(":")
    if not normalized_namespace:
        raise ValueError("Cache namespace must not be empty")
    return f"{normalized_namespace}:{CACHE_KEY_VERSION}:{canonical_sha256(payload)}"


def search_results_cache_key(params: Mapping[str, Any] | MultiValueDict) -> str:
    return build_cache_key("search", params)


def product_detail_cache_key(*, slug: str, shop_slug: str | None = None) -> str:
    return build_cache_key(
        "product",
        {
            "shop_slug": shop_slug or "",
            "slug": slug,
        },
    )


def product_cache_keys(*, slug: str, shop_slug: str | None = None) -> tuple[str, ...]:
    keys = [
        HOME_PAGE_CACHE_KEY,
        product_detail_cache_key(slug=slug),
    ]
    if shop_slug:
        keys.append(product_detail_cache_key(slug=slug, shop_slug=shop_slug))
    return tuple(keys)


def search_suggestions_cache_key(query_prefix: str) -> str:
    normalized_prefix = unicodedata.normalize("NFC", query_prefix).strip().casefold()
    return build_cache_key("suggestions", {"prefix": normalized_prefix})


def safe_cache_get(key: str, default: Any = None) -> Any:
    try:
        return cache.get(key, default)
    except Exception:
        logger.warning(
            "Cache get failed; using fallback",
            extra={"cache_key": key},
            exc_info=True,
        )
        return default


def safe_cache_set(key: str, value: Any, timeout: int | None = None) -> bool:
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        logger.warning(
            "Cache set failed; continuing without cache",
            extra={"cache_key": key},
            exc_info=True,
        )
        return False
    return True


def safe_cache_delete(key: str) -> bool:
    try:
        cache.delete(key)
    except Exception:
        logger.warning(
            "Cache delete failed; stale entry will expire by TTL",
            extra={"cache_key": key},
            exc_info=True,
        )
        return False
    return True


def safe_cache_delete_many(*keys: str) -> bool:
    unique_keys = tuple(dict.fromkeys(key for key in keys if key))
    if not unique_keys:
        return True
    try:
        cache.delete_many(unique_keys)
    except Exception:
        logger.warning(
            "Cache delete-many failed; stale entries will expire by TTL",
            extra={"cache_key_count": len(unique_keys)},
            exc_info=True,
        )
        return False
    return True


def invalidate_cache_keys_on_commit(*keys: str) -> None:
    unique_keys = tuple(dict.fromkeys(key for key in keys if key))
    if unique_keys:
        transaction.on_commit(partial(safe_cache_delete_many, *unique_keys))


def invalidate_product_cache_on_commit(
    *,
    slug: str,
    shop_slug: str | None = None,
) -> None:
    invalidate_cache_keys_on_commit(
        *product_cache_keys(slug=slug, shop_slug=shop_slug),
    )
