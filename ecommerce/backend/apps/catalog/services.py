from collections.abc import Iterable
from uuid import UUID

from django.apps import apps as django_apps
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.common.cache_utils import (
    CATEGORY_TREE_CACHE_KEY,
    HOME_PAGE_CACHE_KEY,
    invalidate_cache_keys_on_commit,
)
from apps.common.exceptions import BusinessError

from .models import Brand, Category

SLUG_MAX_LENGTH = 180


def _normalize_slug(value: str) -> str:
    normalized = slugify(value)[:SLUG_MAX_LENGTH].strip("-")
    if not normalized:
        raise BusinessError(
            "Không thể tạo slug từ dữ liệu đã cung cấp",
            errors={"slug": ["Slug phải chứa ít nhất một ký tự chữ hoặc số"]},
        )
    return normalized


def _resolve_slug(
    *,
    model,
    name: str,
    requested_slug: str | None,
    exclude_id: UUID | None = None,
) -> str:
    base_slug = _normalize_slug(requested_slug if requested_slug is not None else name)
    queryset = model.objects.filter(slug=base_slug)
    if exclude_id is not None:
        queryset = queryset.exclude(pk=exclude_id)

    if requested_slug is not None:
        if queryset.exists():
            raise BusinessError(
                "Slug đã được sử dụng",
                errors={"slug": ["Vui lòng chọn slug khác"]},
            )
        return base_slug

    if not queryset.exists():
        return base_slug

    suffix = 2
    while True:
        suffix_text = f"-{suffix}"
        candidate = f"{base_slug[: SLUG_MAX_LENGTH - len(suffix_text)]}{suffix_text}"
        candidate_queryset = model.objects.filter(slug=candidate)
        if exclude_id is not None:
            candidate_queryset = candidate_queryset.exclude(pk=exclude_id)
        if not candidate_queryset.exists():
            return candidate
        suffix += 1


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise BusinessError(
            "Tên không được để trống",
            errors={"name": ["Tên không được để trống"]},
        )
    return cleaned


class CategoryService:
    @staticmethod
    def validate_no_cycle(*, category: Category | None, parent: Category | None) -> None:
        if parent is None:
            return
        if parent.is_deleted:
            raise BusinessError(
                "Không thể sử dụng danh mục cha đã bị xóa",
                errors={"parent": ["Danh mục cha không hợp lệ"]},
            )

        category_id = category.pk if category is not None else None
        visited: set[UUID] = set()
        current: Category | None = parent
        while current is not None:
            if current.pk == category_id or current.pk in visited:
                raise BusinessError(
                    "Danh mục cha tạo ra vòng lặp",
                    errors={"parent": ["Cây danh mục không được có vòng lặp"]},
                )
            visited.add(current.pk)
            if current.parent_id is None:
                current = None
            else:
                current = (
                    Category.objects.only("id", "parent_id", "is_deleted")
                    .filter(pk=current.parent_id)
                    .first()
                )

    @staticmethod
    def _validate_parent_map(parent_map: dict[UUID, UUID | None]) -> None:
        for category_id in parent_map:
            visited: set[UUID] = set()
            current_id: UUID | None = category_id
            while current_id is not None:
                if current_id in visited:
                    raise BusinessError(
                        "Thứ tự danh mục tạo ra vòng lặp",
                        errors={"items": ["Cây danh mục không được có vòng lặp"]},
                    )
                visited.add(current_id)
                current_id = parent_map.get(current_id)

    @staticmethod
    def create(
        *,
        name: str,
        parent: Category | None = None,
        slug: str | None = None,
        image_url: str | None = None,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> Category:
        cleaned_name = _clean_name(name)
        CategoryService.validate_no_cycle(category=None, parent=parent)
        resolved_slug = _resolve_slug(
            model=Category,
            name=cleaned_name,
            requested_slug=slug,
        )
        try:
            with transaction.atomic():
                return Category.objects.create(
                    parent=parent,
                    name=cleaned_name,
                    slug=resolved_slug,
                    image_url=image_url,
                    sort_order=sort_order,
                    is_active=is_active,
                )
        except IntegrityError as exc:
            raise BusinessError(
                "Không thể tạo danh mục do dữ liệu bị trùng hoặc không hợp lệ",
                errors={"category": ["Vui lòng kiểm tra tên, slug và danh mục cha"]},
            ) from exc

    @staticmethod
    def update(*, category: Category, data: dict) -> Category:
        try:
            with transaction.atomic():
                locked_category = (
                    Category.objects.select_for_update()
                    .filter(pk=category.pk, is_deleted=False)
                    .first()
                )
                if locked_category is None:
                    raise BusinessError("Không tìm thấy danh mục", http_status=404)

                update_fields: set[str] = set()
                if "name" in data:
                    locked_category.name = _clean_name(data["name"])
                    update_fields.add("name")
                if "parent" in data:
                    CategoryService.validate_no_cycle(
                        category=locked_category,
                        parent=data["parent"],
                    )
                    locked_category.parent = data["parent"]
                    update_fields.add("parent")
                if "slug" in data:
                    locked_category.slug = _resolve_slug(
                        model=Category,
                        name=locked_category.name,
                        requested_slug=data["slug"],
                        exclude_id=locked_category.pk,
                    )
                    update_fields.add("slug")
                for field in ("image_url", "sort_order", "is_active"):
                    if field in data:
                        setattr(locked_category, field, data[field])
                        update_fields.add(field)

                if update_fields:
                    update_fields.add("updated_at")
                    locked_category.save(update_fields=update_fields)
                return locked_category
        except IntegrityError as exc:
            raise BusinessError(
                "Không thể cập nhật danh mục do dữ liệu bị trùng hoặc không hợp lệ",
                errors={"category": ["Vui lòng kiểm tra slug và danh mục cha"]},
            ) from exc

    @staticmethod
    def _has_active_products(category: Category) -> bool:
        try:
            product_model = django_apps.get_model("product", "Product")
        except LookupError:
            return False

        filters: dict = {"category_id": category.pk}
        if any(field.name == "is_deleted" for field in product_model._meta.fields):
            filters["is_deleted"] = False
        return product_model._default_manager.filter(**filters).exists()

    @staticmethod
    def soft_delete(*, category: Category) -> Category:
        with transaction.atomic():
            locked_category = (
                Category.objects.select_for_update()
                .filter(pk=category.pk, is_deleted=False)
                .first()
            )
            if locked_category is None:
                raise BusinessError("Không tìm thấy danh mục", http_status=404)
            if locked_category.children.filter(is_deleted=False).exists():
                raise BusinessError(
                    "Không thể xóa danh mục đang có danh mục con",
                    errors={"category": ["Hãy chuyển hoặc xóa các danh mục con trước"]},
                )
            if CategoryService._has_active_products(locked_category):
                raise BusinessError(
                    "Không thể xóa danh mục đang được sản phẩm sử dụng",
                    errors={"category": ["Danh mục vẫn còn sản phẩm chưa xóa"]},
                )

            locked_category.is_active = False
            locked_category.is_deleted = True
            locked_category.deleted_at = timezone.now()
            locked_category.save(
                update_fields=("is_active", "is_deleted", "deleted_at", "updated_at")
            )
            return locked_category

    @staticmethod
    def reorder(*, items: Iterable[dict]) -> list[Category]:
        item_list = list(items)
        category_ids = [item["id"] for item in item_list]

        with transaction.atomic():
            categories = list(
                Category.objects.select_for_update()
                .filter(is_deleted=False)
                .only("id", "parent_id", "sort_order", "updated_at")
            )
            categories_by_id = {category.pk: category for category in categories}
            missing_ids = [
                str(category_id)
                for category_id in category_ids
                if category_id not in categories_by_id
            ]
            if missing_ids:
                raise BusinessError(
                    "Có danh mục không tồn tại",
                    errors={"items": [f"Không tìm thấy: {', '.join(missing_ids)}"]},
                    http_status=404,
                )

            parent_map = {category.pk: category.parent_id for category in categories}
            for item in item_list:
                category = categories_by_id[item["id"]]
                parent_id = item.get("parent_id", category.parent_id)
                if parent_id is not None and parent_id not in categories_by_id:
                    raise BusinessError(
                        "Danh mục cha không tồn tại",
                        errors={"items": [f"Parent {parent_id} không hợp lệ"]},
                        http_status=404,
                    )
                parent_map[category.pk] = parent_id

            CategoryService._validate_parent_map(parent_map)

            now = timezone.now()
            updated_categories: list[Category] = []
            for item in item_list:
                category = categories_by_id[item["id"]]
                category.parent_id = parent_map[category.pk]
                category.sort_order = item["sort_order"]
                category.updated_at = now
                updated_categories.append(category)

            Category.objects.bulk_update(
                updated_categories,
                fields=("parent", "sort_order", "updated_at"),
            )
            invalidate_cache_keys_on_commit(
                CATEGORY_TREE_CACHE_KEY,
                HOME_PAGE_CACHE_KEY,
            )
            return updated_categories


class BrandService:
    @staticmethod
    def _validate_unique_name(*, name: str, exclude_id: UUID | None = None) -> None:
        queryset = Brand.objects.filter(name__iexact=name)
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        if queryset.exists():
            raise BusinessError(
                "Tên thương hiệu đã được sử dụng",
                errors={"name": ["Vui lòng chọn tên khác"]},
            )

    @staticmethod
    def create(
        *,
        name: str,
        slug: str | None = None,
        logo_url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> Brand:
        cleaned_name = _clean_name(name)
        BrandService._validate_unique_name(name=cleaned_name)
        resolved_slug = _resolve_slug(
            model=Brand,
            name=cleaned_name,
            requested_slug=slug,
        )
        try:
            with transaction.atomic():
                return Brand.objects.create(
                    name=cleaned_name,
                    slug=resolved_slug,
                    logo_url=logo_url,
                    description=description,
                    is_active=is_active,
                )
        except IntegrityError as exc:
            raise BusinessError(
                "Không thể tạo thương hiệu do tên hoặc slug bị trùng",
                errors={"brand": ["Vui lòng kiểm tra tên và slug"]},
            ) from exc

    @staticmethod
    def update(*, brand: Brand, data: dict) -> Brand:
        try:
            with transaction.atomic():
                locked_brand = (
                    Brand.objects.select_for_update().filter(pk=brand.pk, is_deleted=False).first()
                )
                if locked_brand is None:
                    raise BusinessError("Không tìm thấy thương hiệu", http_status=404)

                update_fields: set[str] = set()
                if "name" in data:
                    cleaned_name = _clean_name(data["name"])
                    BrandService._validate_unique_name(
                        name=cleaned_name,
                        exclude_id=locked_brand.pk,
                    )
                    locked_brand.name = cleaned_name
                    update_fields.add("name")
                if "slug" in data:
                    locked_brand.slug = _resolve_slug(
                        model=Brand,
                        name=locked_brand.name,
                        requested_slug=data["slug"],
                        exclude_id=locked_brand.pk,
                    )
                    update_fields.add("slug")
                for field in ("logo_url", "description", "is_active"):
                    if field in data:
                        setattr(locked_brand, field, data[field])
                        update_fields.add(field)

                if update_fields:
                    update_fields.add("updated_at")
                    locked_brand.save(update_fields=update_fields)
                return locked_brand
        except IntegrityError as exc:
            raise BusinessError(
                "Không thể cập nhật thương hiệu do tên hoặc slug bị trùng",
                errors={"brand": ["Vui lòng kiểm tra tên và slug"]},
            ) from exc

    @staticmethod
    def soft_delete(*, brand: Brand) -> Brand:
        with transaction.atomic():
            locked_brand = (
                Brand.objects.select_for_update().filter(pk=brand.pk, is_deleted=False).first()
            )
            if locked_brand is None:
                raise BusinessError("Không tìm thấy thương hiệu", http_status=404)

            locked_brand.is_active = False
            locked_brand.is_deleted = True
            locked_brand.deleted_at = timezone.now()
            locked_brand.save(update_fields=("is_active", "is_deleted", "deleted_at", "updated_at"))
            return locked_brand
