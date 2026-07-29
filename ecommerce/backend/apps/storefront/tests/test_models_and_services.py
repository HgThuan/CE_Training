from datetime import timedelta

import pytest
from django.utils import timezone

from apps.common.exceptions import BusinessError
from apps.storefront.models import Banner
from apps.storefront.selectors import get_active_banners
from apps.storefront.services import BannerService


@pytest.mark.django_db
def test_banner_service_crud_and_soft_delete():
    banner = BannerService.create(
        data={
            "title": "Khuyến mãi mùa hè",
            "image_url": "https://cdn.example.com/banner.webp",
            "position": Banner.Position.HERO,
        }
    )
    updated = BannerService.update(
        banner=banner,
        data={"title": "Khuyến mãi mới", "sort_order": 3},
    )
    deleted = BannerService.soft_delete(banner=updated)

    assert updated.title == "Khuyến mãi mới"
    assert updated.sort_order == 3
    assert deleted.is_active is False
    assert deleted.is_deleted is True
    assert deleted.deleted_at is not None


@pytest.mark.django_db
def test_banner_service_rejects_invalid_schedule():
    starts_at = timezone.now()

    with pytest.raises(BusinessError, match="không hợp lệ"):
        BannerService.create(
            data={
                "image_url": "https://cdn.example.com/banner.webp",
                "starts_at": starts_at,
                "ends_at": starts_at,
            }
        )


@pytest.mark.django_db
def test_active_banner_selector_applies_window_and_position():
    now = timezone.now()
    visible = Banner.objects.create(
        image_url="https://cdn.example.com/visible.webp",
        position=Banner.Position.HERO,
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(minutes=1),
        sort_order=2,
    )
    Banner.objects.create(
        image_url="https://cdn.example.com/future.webp",
        starts_at=now + timedelta(minutes=1),
    )
    Banner.objects.create(
        image_url="https://cdn.example.com/expired.webp",
        ends_at=now - timedelta(minutes=1),
    )
    Banner.objects.create(
        image_url="https://cdn.example.com/inactive.webp",
        is_active=False,
    )
    Banner.objects.create(
        image_url="https://cdn.example.com/middle.webp",
        position=Banner.Position.MIDDLE,
    )

    assert list(get_active_banners(Banner.Position.HERO)) == [visible]


@pytest.mark.django_db
def test_banner_reorder_swaps_sort_order_atomically():
    first = Banner.objects.create(
        image_url="https://cdn.example.com/first.webp",
        sort_order=1,
    )
    second = Banner.objects.create(
        image_url="https://cdn.example.com/second.webp",
        sort_order=9,
    )

    reordered = BannerService.reorder(source_id=first.pk, target_id=second.pk)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.sort_order == 9
    assert second.sort_order == 1
    assert {banner.pk for banner in reordered} == {first.pk, second.pk}
