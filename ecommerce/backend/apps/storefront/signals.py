from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.cache_utils import HOME_PAGE_CACHE_KEY, invalidate_cache_keys_on_commit

from .models import Banner


@receiver(
    (post_save, post_delete),
    sender=Banner,
    dispatch_uid="storefront.invalidate_home_on_banner_change",
)
def invalidate_home_on_banner_change(**kwargs) -> None:
    invalidate_cache_keys_on_commit(HOME_PAGE_CACHE_KEY)
