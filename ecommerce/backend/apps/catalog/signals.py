from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.cache_utils import (
    CATEGORY_TREE_CACHE_KEY,
    HOME_PAGE_CACHE_KEY,
    invalidate_cache_keys_on_commit,
)

from .models import Category


@receiver(
    (post_save, post_delete),
    sender=Category,
    dispatch_uid="catalog.invalidate_category_caches",
)
def invalidate_category_caches(**kwargs) -> None:
    invalidate_cache_keys_on_commit(
        CATEGORY_TREE_CACHE_KEY,
        HOME_PAGE_CACHE_KEY,
    )
