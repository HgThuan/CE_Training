from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import BusinessError

from .models import Banner


class BannerService:
    WRITABLE_FIELDS = {
        "title",
        "image_url",
        "target_url",
        "position",
        "sort_order",
        "starts_at",
        "ends_at",
        "is_active",
    }

    @staticmethod
    def _validate_schedule(*, starts_at, ends_at) -> None:
        if starts_at and ends_at and ends_at <= starts_at:
            raise BusinessError(
                "Thời gian banner không hợp lệ",
                errors={"ends_at": ["Thời gian kết thúc phải sau thời gian bắt đầu"]},
            )

    @staticmethod
    @transaction.atomic
    def create(*, data: dict) -> Banner:
        payload = {
            key: value for key, value in data.items() if key in BannerService.WRITABLE_FIELDS
        }
        BannerService._validate_schedule(
            starts_at=payload.get("starts_at"),
            ends_at=payload.get("ends_at"),
        )
        return Banner.objects.create(**payload)

    @staticmethod
    @transaction.atomic
    def update(*, banner: Banner, data: dict) -> Banner:
        locked = Banner.objects.select_for_update().filter(pk=banner.pk, is_deleted=False).first()
        if locked is None:
            raise BusinessError("Không tìm thấy banner", http_status=404)

        payload = {
            key: value for key, value in data.items() if key in BannerService.WRITABLE_FIELDS
        }
        BannerService._validate_schedule(
            starts_at=payload.get("starts_at", locked.starts_at),
            ends_at=payload.get("ends_at", locked.ends_at),
        )
        update_fields: set[str] = set()
        for field, value in payload.items():
            setattr(locked, field, value)
            update_fields.add(field)
        if update_fields:
            update_fields.add("updated_at")
            locked.save(update_fields=update_fields)
        return locked

    @staticmethod
    @transaction.atomic
    def soft_delete(*, banner: Banner) -> Banner:
        locked = Banner.objects.select_for_update().filter(pk=banner.pk, is_deleted=False).first()
        if locked is None:
            raise BusinessError("Không tìm thấy banner", http_status=404)
        locked.is_active = False
        locked.is_deleted = True
        locked.deleted_at = timezone.now()
        locked.save(update_fields=("is_active", "is_deleted", "deleted_at", "updated_at"))
        return locked

    @staticmethod
    @transaction.atomic
    def reorder(*, source_id, target_id) -> list[Banner]:
        banners = list(
            Banner.objects.select_for_update()
            .filter(pk__in=(source_id, target_id), is_deleted=False)
            .order_by("id")
        )
        if len(banners) != 2:
            raise BusinessError(
                "Không tìm thấy banner cần sắp xếp",
                errors={"banners": ["Banner nguồn hoặc đích không tồn tại"]},
                http_status=404,
            )
        by_id = {banner.pk: banner for banner in banners}
        source = by_id[source_id]
        target = by_id[target_id]
        source.sort_order, target.sort_order = target.sort_order, source.sort_order
        now = timezone.now()
        source.updated_at = now
        target.updated_at = now
        Banner.objects.bulk_update(
            (source, target),
            fields=("sort_order", "updated_at"),
        )
        return [source, target]
