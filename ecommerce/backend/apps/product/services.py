import logging
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from html import escape
from html.parser import HTMLParser
from itertools import product as cartesian_product
from pathlib import PurePosixPath
from urllib.parse import urlparse
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Max, Min
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, UnidentifiedImageError

from apps.account.models import Shop, User
from apps.account.selectors import get_shop_for_owner
from apps.account.services import ShopBusinessPolicy
from apps.catalog.models import Brand, Category
from apps.common.cache_utils import invalidate_product_cache_on_commit
from apps.common.exceptions import BusinessError
from apps.common.models import AuditLog

from .models import (
    Attribute,
    AttributeValue,
    Product,
    ProductAttributeValue,
    ProductMedia,
    ProductVariant,
    VariantAttributeValue,
)
from .state_machine import ProductStateMachine

logger = logging.getLogger(__name__)

PRODUCT_SLUG_MAX_LENGTH = 280
MAX_PRODUCT_IMAGES = 9
MAX_PRODUCT_VIDEOS = 1
ALLOWED_IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}
VIDEO_SIGNATURES = {
    "mp4": "video/mp4",
    "webm": "video/webm",
}


class _ProductDescriptionSanitizer(HTMLParser):
    """Small allow-list sanitizer for product rich text without external dependencies."""

    ALLOWED_TAGS = {
        "p",
        "br",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "ul",
        "ol",
        "li",
        "blockquote",
        "h2",
        "h3",
        "a",
    }
    VOID_TAGS = {"br"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.ALLOWED_TAGS:
            return
        rendered_attrs = ""
        if tag == "a":
            safe_attrs: list[str] = []
            for name, value in attrs:
                if name not in {"href", "title"} or value is None:
                    continue
                if name == "href":
                    parsed = urlparse(value.strip())
                    if parsed.scheme and parsed.scheme not in {"http", "https", "mailto"}:
                        continue
                safe_attrs.append(f'{name}="{escape(value, quote=True)}"')
            safe_attrs.extend(['rel="noopener noreferrer"', 'target="_blank"'])
            rendered_attrs = f" {' '.join(safe_attrs)}"
        self.parts.append(f"<{tag}{rendered_attrs}>")

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ALLOWED_TAGS and tag not in self.VOID_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(escape(data))

    def get_html(self) -> str:
        return "".join(self.parts).strip()


def _sanitize_description(value: str | None) -> str | None:
    if value is None:
        return None
    parser = _ProductDescriptionSanitizer()
    parser.feed(value)
    parser.close()
    return parser.get_html()


def _clean_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise BusinessError(
            "Tên sản phẩm không được để trống",
            errors={"name": ["Tên sản phẩm không được để trống"]},
        )
    return normalized


def _normalize_slug(value: str) -> str:
    normalized = slugify(value)[:PRODUCT_SLUG_MAX_LENGTH].strip("-")
    if not normalized:
        raise BusinessError(
            "Slug sản phẩm không hợp lệ",
            errors={"slug": ["Slug phải có ít nhất một ký tự chữ hoặc số"]},
        )
    return normalized


def _resolve_product_slug(
    *,
    shop: Shop,
    name: str,
    requested_slug: str | None,
    exclude_product_id=None,
) -> str:
    base_slug = _normalize_slug(requested_slug if requested_slug is not None else name)
    queryset = Product.objects.filter(
        shop=shop,
        slug=base_slug,
        is_deleted=False,
    )
    if exclude_product_id is not None:
        queryset = queryset.exclude(pk=exclude_product_id)
    if not queryset.exists():
        return base_slug
    if requested_slug is not None:
        raise BusinessError(
            "Slug sản phẩm đã được sử dụng trong gian hàng",
            errors={"slug": ["Vui lòng chọn slug khác"]},
        )

    suffix = 2
    while True:
        suffix_text = f"-{suffix}"
        candidate = f"{base_slug[: PRODUCT_SLUG_MAX_LENGTH - len(suffix_text)]}{suffix_text}"
        if not Product.objects.filter(
            shop=shop,
            slug=candidate,
            is_deleted=False,
        ).exists():
            return candidate
        suffix += 1


def _get_seller_shop(seller_user) -> Shop:
    if seller_user.role != User.Role.SELLER or not seller_user.is_active or seller_user.is_deleted:
        raise BusinessError(
            "Tài khoản không có quyền quản lý sản phẩm",
            errors={"role": ["Yêu cầu tài khoản Seller đang hoạt động"]},
            http_status=403,
        )
    shop = get_shop_for_owner(seller_user)
    if shop is None:
        raise BusinessError("Không tìm thấy gian hàng của Seller", http_status=404)
    return shop


def _lock_owned_product(*, seller_user, product_id) -> tuple[Product, Shop]:
    shop = _get_seller_shop(seller_user)
    product = (
        Product.objects.select_for_update(of=("self",))
        .select_related("shop", "category", "brand")
        .filter(
            pk=product_id,
            shop_id=shop.pk,
            is_deleted=False,
        )
        .first()
    )
    if product is None:
        raise BusinessError(
            "Bạn không có quyền thao tác sản phẩm này",
            errors={"product": ["Sản phẩm không thuộc gian hàng của bạn"]},
            http_status=403,
        )
    return product, shop


def _assert_admin(user) -> None:
    if user.role != User.Role.ADMIN or not user.is_active or user.is_deleted:
        raise BusinessError(
            "Chỉ Admin được thực hiện thao tác này",
            errors={"role": ["Yêu cầu tài khoản Admin đang hoạt động"]},
            http_status=403,
        )


def _validate_catalog_relations(
    *,
    category: Category,
    brand: Brand | None,
) -> tuple[Category, Brand | None]:
    active_category = (
        Category.objects.select_for_update()
        .filter(pk=category.pk, is_active=True, is_deleted=False)
        .first()
    )
    if active_category is None:
        raise BusinessError(
            "Danh mục không khả dụng",
            errors={"category": ["Vui lòng chọn danh mục đang hoạt động"]},
        )
    active_brand = None
    if brand is not None:
        active_brand = (
            Brand.objects.select_for_update()
            .filter(pk=brand.pk, is_active=True, is_deleted=False)
            .first()
        )
        if active_brand is None:
            raise BusinessError(
                "Thương hiệu không khả dụng",
                errors={"brand": ["Vui lòng chọn thương hiệu đang hoạt động"]},
            )
    return active_category, active_brand


class ProductService:
    EDITABLE_STATUSES = {Product.Status.DRAFT, Product.Status.REJECTED}
    WRITABLE_FIELDS = {
        "category",
        "brand",
        "name",
        "slug",
        "short_description",
        "description",
    }

    @staticmethod
    @transaction.atomic
    def create_product(*, seller_user, data: dict) -> Product:
        shop = _get_seller_shop(seller_user)
        ShopBusinessPolicy.ensure_can_create_new_resource(shop=shop)

        try:
            category = data["category"]
            name = _clean_name(data["name"])
        except KeyError as exc:
            field = str(exc).strip("'")
            raise BusinessError(
                "Thiếu dữ liệu bắt buộc",
                errors={field: ["Trường này là bắt buộc"]},
            ) from exc

        brand = data.get("brand")
        category, brand = _validate_catalog_relations(
            category=category,
            brand=brand,
        )
        slug = _resolve_product_slug(
            shop=shop,
            name=name,
            requested_slug=data.get("slug"),
        )
        try:
            return Product.objects.create(
                shop=shop,
                category=category,
                brand=brand,
                name=name,
                slug=slug,
                short_description=data.get("short_description"),
                description=_sanitize_description(data.get("description")),
                status=Product.Status.DRAFT,
            )
        except IntegrityError as exc:
            raise BusinessError(
                "Không thể tạo sản phẩm do dữ liệu bị trùng hoặc không hợp lệ",
                errors={"product": ["Vui lòng kiểm tra slug và dữ liệu sản phẩm"]},
            ) from exc

    @staticmethod
    @transaction.atomic
    def update_product(
        *,
        product: Product,
        seller_user,
        data: dict,
        request_id: str = "",
    ) -> Product:
        locked_product, _shop = _lock_owned_product(
            seller_user=seller_user,
            product_id=product.pk,
        )
        if locked_product.status not in ProductService.EDITABLE_STATUSES:
            raise BusinessError(
                "Không thể sửa sản phẩm ở trạng thái hiện tại",
                errors={"status": ["Chỉ sản phẩm nháp hoặc bị từ chối mới được Seller chỉnh sửa"]},
            )

        updates = {
            key: value for key, value in data.items() if key in ProductService.WRITABLE_FIELDS
        }
        if "name" in updates:
            updates["name"] = _clean_name(updates["name"])
        category, brand = _validate_catalog_relations(
            category=updates.get("category", locked_product.category),
            brand=updates.get("brand", locked_product.brand),
        )
        if "category" in updates:
            updates["category"] = category
        if "brand" in updates:
            updates["brand"] = brand
        if "slug" in updates:
            updates["slug"] = _resolve_product_slug(
                shop=locked_product.shop,
                name=updates.get("name", locked_product.name),
                requested_slug=updates["slug"],
                exclude_product_id=locked_product.pk,
            )
        if "description" in updates:
            updates["description"] = _sanitize_description(updates["description"])

        for field, value in updates.items():
            setattr(locked_product, field, value)
        if updates:
            try:
                locked_product.save(update_fields=(*updates.keys(), "updated_at"))
            except IntegrityError as exc:
                raise BusinessError(
                    "Không thể cập nhật sản phẩm do dữ liệu bị trùng hoặc không hợp lệ",
                    errors={"product": ["Vui lòng kiểm tra slug và dữ liệu sản phẩm"]},
                ) from exc

        if updates and locked_product.status == Product.Status.REJECTED:
            locked_product = ProductStateMachine.transition(
                locked_product,
                Product.Status.DRAFT,
                actor=seller_user,
                note="Seller đã chỉnh sửa sản phẩm bị từ chối",
                request_id=request_id,
            )
        return locked_product

    @staticmethod
    @transaction.atomic
    def soft_delete_product(*, product: Product, seller_user) -> Product:
        locked_product, _shop = _lock_owned_product(
            seller_user=seller_user,
            product_id=product.pk,
        )
        if not ProductStateMachine.can_soft_delete(locked_product):
            raise BusinessError(
                "Không thể xóa sản phẩm ở trạng thái hiện tại",
                errors={"status": ["Chỉ sản phẩm nháp hoặc đang ẩn mới được xóa"]},
            )
        locked_product.is_deleted = True
        locked_product.deleted_at = timezone.now()
        locked_product.save(update_fields=("is_deleted", "deleted_at", "updated_at"))
        return locked_product

    @staticmethod
    @transaction.atomic
    def admin_soft_delete(
        *,
        product: Product,
        admin_user,
        request_id: str = "",
    ) -> Product:
        _assert_admin(admin_user)
        locked_product = (
            Product.objects.select_for_update().filter(pk=product.pk, is_deleted=False).first()
        )
        if locked_product is None:
            raise BusinessError("Không tìm thấy sản phẩm", http_status=404)
        if not ProductStateMachine.can_soft_delete(locked_product):
            raise BusinessError(
                "Không thể xóa sản phẩm ở trạng thái hiện tại",
                errors={"status": ["Admin chỉ được xóa sản phẩm nháp hoặc đang ẩn"]},
            )
        locked_product.is_deleted = True
        locked_product.deleted_at = timezone.now()
        locked_product.save(update_fields=("is_deleted", "deleted_at", "updated_at"))
        AuditLog.objects.create(
            actor=admin_user,
            action="delete_product",
            target_type="Product",
            target_id=str(locked_product.pk),
            request_id=request_id,
            diff={"is_deleted": {"before": False, "after": True}},
        )
        logger.info(
            "Admin soft-deleted product",
            extra={
                "request_id": request_id,
                "user_id": admin_user.pk,
                "product_id": str(locked_product.pk),
            },
        )
        return locked_product

    @staticmethod
    @transaction.atomic
    def submit_for_review(
        *,
        product: Product,
        actor,
        request_id: str = "",
    ) -> Product:
        locked_product, shop = _lock_owned_product(
            seller_user=actor,
            product_id=product.pk,
        )
        ShopBusinessPolicy.ensure_can_create_new_resource(shop=shop)
        if not ProductVariant.objects.filter(
            product_id=locked_product.pk,
            is_active=True,
            is_deleted=False,
        ).exists():
            raise BusinessError(
                "Sản phẩm cần ít nhất một SKU khả dụng trước khi gửi duyệt",
                errors={"variants": ["Hãy tạo và kích hoạt ít nhất một biến thể"]},
            )
        return ProductStateMachine.transition(
            locked_product,
            Product.Status.PENDING_REVIEW,
            actor=actor,
            request_id=request_id,
        )

    @staticmethod
    @transaction.atomic
    def admin_approve(
        *,
        product: Product,
        admin_user,
        request_id: str = "",
    ) -> Product:
        _assert_admin(admin_user)
        if not ProductVariant.objects.filter(
            product_id=product.pk,
            is_active=True,
            is_deleted=False,
        ).exists():
            raise BusinessError(
                "Không thể duyệt sản phẩm chưa có SKU khả dụng",
                errors={"variants": ["Sản phẩm phải có ít nhất một biến thể"]},
            )
        approved_product = ProductStateMachine.transition(
            product,
            Product.Status.APPROVED,
            actor=admin_user,
            request_id=request_id,
        )
        approved_product.approved_by = admin_user
        approved_product.approved_at = timezone.now()
        approved_product.save(update_fields=("approved_by", "approved_at", "updated_at"))
        return approved_product

    @staticmethod
    def admin_reject(
        *,
        product: Product,
        admin_user,
        reason: str,
        request_id: str = "",
    ) -> Product:
        _assert_admin(admin_user)
        return ProductStateMachine.transition(
            product,
            Product.Status.REJECTED,
            actor=admin_user,
            note=reason,
            request_id=request_id,
        )

    @staticmethod
    def admin_hide(
        *,
        product: Product,
        admin_user,
        request_id: str = "",
    ) -> Product:
        _assert_admin(admin_user)
        return ProductStateMachine.transition(
            product,
            Product.Status.HIDDEN,
            actor=admin_user,
            request_id=request_id,
        )

    @staticmethod
    @transaction.atomic
    def update_price_cache(*, product: Product) -> Product:
        locked_product = (
            Product.objects.select_for_update().filter(pk=product.pk, is_deleted=False).first()
        )
        if locked_product is None:
            raise BusinessError("Không tìm thấy sản phẩm", http_status=404)
        price_range = ProductVariant.objects.filter(
            product=locked_product,
            is_active=True,
            is_deleted=False,
        ).aggregate(
            min_price=Min("sale_price"),
            max_price=Max("sale_price"),
        )
        locked_product.min_price = price_range["min_price"]
        locked_product.max_price = price_range["max_price"]
        locked_product.save(update_fields=("min_price", "max_price", "updated_at"))
        return locked_product


class AttributeService:
    @staticmethod
    @transaction.atomic
    def create_attribute(*, seller_user, data: dict) -> Attribute:
        shop = _get_seller_shop(seller_user)
        ShopBusinessPolicy.ensure_can_create_new_resource(shop=shop)

        name = str(data.get("name", "")).strip()
        if not name:
            raise BusinessError(
                "Tên thuộc tính không được để trống",
                errors={"name": ["Trường này là bắt buộc"]},
            )
        code = str(data.get("code") or slugify(name)).strip().lower()[:100]
        if not code:
            raise BusinessError(
                "Mã thuộc tính không hợp lệ",
                errors={"code": ["Hãy nhập mã gồm chữ hoặc số"]},
            )

        raw_values = data.get("values") or []
        normalized_values: list[dict] = []
        seen_values: set[str] = set()
        for index, raw_value in enumerate(raw_values):
            value = str(raw_value.get("value", "")).strip()
            if not value:
                raise BusinessError(
                    "Giá trị thuộc tính không được để trống",
                    errors={"values": [f"Giá trị ở vị trí {index + 1} không hợp lệ"]},
                )
            normalized = value.casefold()
            if normalized in seen_values:
                raise BusinessError(
                    "Giá trị thuộc tính bị trùng",
                    errors={"values": [f"Giá trị “{value}” xuất hiện nhiều lần"]},
                )
            seen_values.add(normalized)
            normalized_values.append(
                {
                    "value": value,
                    "display_value": str(raw_value.get("display_value") or "").strip() or None,
                    "color_code": str(raw_value.get("color_code") or "").strip() or None,
                    "sort_order": index,
                }
            )
        if not normalized_values:
            raise BusinessError(
                "Thuộc tính cần ít nhất một giá trị",
                errors={"values": ["Hãy nhập ít nhất một giá trị, ví dụ Đỏ hoặc XL"]},
            )

        try:
            attribute = Attribute.objects.create(
                shop=shop,
                name=name,
                code=code,
                display_type=data.get("display_type", Attribute.DisplayType.TEXT),
                sort_order=data.get("sort_order", 0),
            )
            AttributeValue.objects.bulk_create(
                [
                    AttributeValue(attribute=attribute, **value_data)
                    for value_data in normalized_values
                ]
            )
        except IntegrityError as exc:
            raise BusinessError(
                "Thuộc tính đã tồn tại trong gian hàng",
                errors={"name": ["Tên hoặc mã thuộc tính đã được sử dụng"]},
            ) from exc
        return attribute


class MediaService:
    @staticmethod
    def _validate_upload(*, uploaded_file, media_type: str) -> tuple[str, str]:
        if media_type not in ProductMedia.MediaType.values:
            raise BusinessError(
                "Loại media không hợp lệ",
                errors={"media_type": ["Chỉ chấp nhận IMAGE hoặc VIDEO"]},
            )
        max_mb = (
            settings.MAX_IMAGE_UPLOAD_MB
            if media_type == ProductMedia.MediaType.IMAGE
            else settings.MAX_VIDEO_UPLOAD_MB
        )
        if uploaded_file.size <= 0 or uploaded_file.size > max_mb * 1024 * 1024:
            raise BusinessError(
                "Kích thước media không hợp lệ",
                errors={"file": [f"Tệp phải lớn hơn 0 byte và không quá {max_mb} MB"]},
            )

        if media_type == ProductMedia.MediaType.IMAGE:
            try:
                uploaded_file.seek(0)
                with Image.open(uploaded_file) as image:
                    detected_format = image.format
                    image.verify()
                uploaded_file.seek(0)
                with Image.open(uploaded_file) as image:
                    if image.width * image.height > 40_000_000:
                        raise BusinessError(
                            "Ảnh có độ phân giải quá lớn",
                            errors={"file": ["Ảnh không được vượt quá 40 triệu điểm ảnh"]},
                        )
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                raise BusinessError(
                    "Nội dung tệp ảnh không hợp lệ",
                    errors={"file": ["Tệp phải là JPEG, PNG hoặc WebP hợp lệ"]},
                ) from exc
            if detected_format not in ALLOWED_IMAGE_FORMATS:
                raise BusinessError(
                    "Định dạng ảnh không được hỗ trợ",
                    errors={"file": ["Chỉ chấp nhận JPEG, PNG hoặc WebP"]},
                )
            uploaded_file.seek(0)
            return ALLOWED_IMAGE_FORMATS[detected_format]

        uploaded_file.seek(0)
        header = uploaded_file.read(32)
        uploaded_file.seek(0)
        if len(header) >= 12 and header[4:8] == b"ftyp":
            return VIDEO_SIGNATURES["mp4"], "mp4"
        if header.startswith(b"\x1a\x45\xdf\xa3"):
            return VIDEO_SIGNATURES["webm"], "webm"
        raise BusinessError(
            "Nội dung tệp video không hợp lệ",
            errors={"file": ["Chỉ chấp nhận MP4 hoặc WebM có chữ ký tệp hợp lệ"]},
        )

    @staticmethod
    def _storage_name_from_url(file_url: str) -> str | None:
        parsed = urlparse(file_url)
        if parsed.scheme or parsed.netloc:
            return None
        media_path = urlparse(settings.MEDIA_URL).path
        path = parsed.path
        if media_path and path.startswith(media_path):
            return path[len(media_path) :].lstrip("/")
        if not path.startswith("/"):
            return path
        return None

    @staticmethod
    @transaction.atomic
    def upload_media(
        *,
        product: Product,
        uploaded_file,
        media_type: str,
        seller_user,
        variant_id=None,
    ) -> ProductMedia:
        locked_product, _shop = _lock_owned_product(
            seller_user=seller_user,
            product_id=product.pk,
        )
        variant = None
        if variant_id is not None:
            if media_type != ProductMedia.MediaType.IMAGE:
                raise BusinessError(
                    "Media riêng của biến thể phải là ảnh",
                    errors={"variant_id": ["Không thể gán video cho một biến thể"]},
                )
            variant = (
                ProductVariant.objects.select_for_update()
                .filter(
                    pk=variant_id,
                    product=locked_product,
                    shop_id=locked_product.shop_id,
                    is_deleted=False,
                )
                .first()
            )
            if variant is None:
                raise BusinessError(
                    "Không tìm thấy biến thể thuộc sản phẩm",
                    errors={"variant_id": ["Biến thể không hợp lệ"]},
                    http_status=404,
                )
        max_items = (
            MAX_PRODUCT_IMAGES if media_type == ProductMedia.MediaType.IMAGE else MAX_PRODUCT_VIDEOS
        )
        current_count = ProductMedia.objects.filter(
            product=locked_product,
            media_type=media_type,
        ).count()
        is_variant_image_replacement = bool(
            variant
            and ProductMedia.objects.filter(
                product=locked_product,
                variant=variant,
                media_type=ProductMedia.MediaType.IMAGE,
            ).exists()
        )
        if current_count >= max_items and not is_variant_image_replacement:
            raise BusinessError(
                "Đã vượt giới hạn media của sản phẩm",
                errors={"file": ["Mỗi sản phẩm chỉ được tối đa 9 ảnh và 1 video"]},
            )

        _mime_type, extension = MediaService._validate_upload(
            uploaded_file=uploaded_file,
            media_type=media_type,
        )
        storage_name = (
            PurePosixPath("products")
            / str(locked_product.shop_id)
            / str(locked_product.pk)
            / f"{uuid4().hex}.{extension}"
        ).as_posix()
        saved_name = default_storage.save(storage_name, uploaded_file)
        try:
            sort_order = (
                ProductMedia.objects.filter(product=locked_product).aggregate(
                    highest=Max("sort_order")
                )["highest"]
                or 0
            )
            return ProductMedia.objects.create(
                product=locked_product,
                variant=variant,
                media_type=media_type,
                file_url=default_storage.url(saved_name),
                sort_order=sort_order + 1,
            )
        except Exception:
            default_storage.delete(saved_name)
            raise

    @staticmethod
    @transaction.atomic
    def delete_media(*, media: ProductMedia, seller_user) -> None:
        locked_product, _shop = _lock_owned_product(
            seller_user=seller_user,
            product_id=media.product_id,
        )
        locked_media = (
            ProductMedia.objects.select_for_update()
            .select_related("product__shop")
            .filter(pk=media.pk, product=locked_product)
            .first()
        )
        if locked_media is None:
            raise BusinessError("Không tìm thấy media", http_status=404)
        storage_name = MediaService._storage_name_from_url(locked_media.file_url)
        locked_media.delete()
        if storage_name:
            transaction.on_commit(lambda: default_storage.delete(storage_name))

    @staticmethod
    @transaction.atomic
    def reorder_media(
        *,
        product: Product,
        ordered_ids,
        seller_user,
    ) -> list[ProductMedia]:
        locked_product, shop = _lock_owned_product(
            seller_user=seller_user,
            product_id=product.pk,
        )
        normalized_ids = [str(media_id) for media_id in ordered_ids]
        if len(normalized_ids) != len(set(normalized_ids)):
            raise BusinessError(
                "Danh sách media bị trùng",
                errors={"ordered_ids": ["Mỗi media chỉ được xuất hiện một lần"]},
            )
        media_items = list(ProductMedia.objects.select_for_update().filter(product=locked_product))
        by_id = {str(media.pk): media for media in media_items}
        if set(normalized_ids) != set(by_id):
            raise BusinessError(
                "Danh sách media không khớp với sản phẩm",
                errors={
                    "ordered_ids": ["Phải cung cấp đầy đủ và chỉ gồm media của sản phẩm hiện tại"]
                },
            )
        now = timezone.now()
        ordered_media: list[ProductMedia] = []
        for sort_order, media_id in enumerate(normalized_ids):
            media = by_id[media_id]
            media.sort_order = sort_order
            media.updated_at = now
            ordered_media.append(media)
        ProductMedia.objects.bulk_update(
            ordered_media,
            ("sort_order", "updated_at"),
        )
        invalidate_product_cache_on_commit(
            slug=locked_product.slug,
            shop_slug=shop.slug,
        )
        return ordered_media

    @staticmethod
    @transaction.atomic
    def set_primary(
        *,
        product: Product,
        media_id,
        seller_user,
    ) -> ProductMedia:
        locked_product, shop = _lock_owned_product(
            seller_user=seller_user,
            product_id=product.pk,
        )
        media = (
            ProductMedia.objects.select_for_update()
            .filter(
                pk=media_id,
                product=locked_product,
                media_type=ProductMedia.MediaType.IMAGE,
            )
            .first()
        )
        if media is None:
            raise BusinessError(
                "Không tìm thấy ảnh thuộc sản phẩm",
                errors={"media_id": ["Chỉ ảnh của sản phẩm mới được đặt làm ảnh chính"]},
                http_status=404,
            )
        ProductMedia.objects.filter(
            product=locked_product,
            is_primary=True,
        ).exclude(pk=media.pk).update(is_primary=False, updated_at=timezone.now())
        if not media.is_primary:
            media.is_primary = True
            media.save(update_fields=("is_primary", "updated_at"))
        invalidate_product_cache_on_commit(
            slug=locked_product.slug,
            shop_slug=shop.slug,
        )
        return media


class VariantService:
    @staticmethod
    def validate_shop_consistency(*, product: Product, shop: Shop) -> None:
        if product.shop_id != shop.pk:
            raise BusinessError(
                "Gian hàng của variant không khớp với sản phẩm",
                errors={"shop": ["Variant phải thuộc cùng gian hàng với sản phẩm"]},
            )

    @staticmethod
    def _generate_sku(
        *,
        product: Product,
        reserved_skus: set[str] | None = None,
    ) -> str:
        reserved_skus = reserved_skus or set()
        base = slugify(product.slug).replace("-", "").upper()[:72] or "PRODUCT"
        next_number = ProductVariant.objects.filter(shop_id=product.shop_id).count() + 1
        while True:
            candidate = f"{base}-{next_number:04d}"[:100]
            if (
                candidate not in reserved_skus
                and not ProductVariant.objects.filter(
                    shop_id=product.shop_id,
                    sku=candidate,
                ).exists()
            ):
                return candidate
            next_number += 1

    @staticmethod
    @transaction.atomic
    def generate_variants(
        *,
        product: Product,
        attribute_value_ids,
        seller_user,
    ) -> list[ProductVariant]:
        locked_product, shop = _lock_owned_product(
            seller_user=seller_user,
            product_id=product.pk,
        )
        ShopBusinessPolicy.ensure_can_create_new_resource(shop=shop)
        if locked_product.status not in ProductService.EDITABLE_STATUSES:
            raise BusinessError(
                "Chỉ sản phẩm nháp hoặc bị từ chối mới được tạo biến thể",
                errors={"status": ["Trạng thái sản phẩm không cho phép tạo SKU"]},
            )
        if ProductVariant.objects.filter(
            product=locked_product,
            is_deleted=False,
        ).exists():
            raise BusinessError(
                "Sản phẩm đã có biến thể",
                errors={"variants": ["Hãy cập nhật biến thể hiện có"]},
            )

        normalized_ids = list(dict.fromkeys(str(value_id) for value_id in attribute_value_ids))
        if not normalized_ids:
            raise BusinessError(
                "Cần chọn ít nhất một giá trị thuộc tính",
                errors={"attribute_value_ids": ["Danh sách không được để trống"]},
            )
        values = list(
            AttributeValue.objects.select_related("attribute")
            .filter(pk__in=normalized_ids)
            .order_by("attribute__sort_order", "attribute__name", "sort_order", "value")
        )
        if len(values) != len(normalized_ids):
            raise BusinessError(
                "Có giá trị thuộc tính không tồn tại",
                errors={"attribute_value_ids": ["Vui lòng chỉ chọn các giá trị thuộc tính hợp lệ"]},
            )
        for value in values:
            if value.attribute.shop_id not in {None, locked_product.shop_id}:
                raise BusinessError(
                    "Thuộc tính không thuộc gian hàng",
                    errors={
                        "attribute_value_ids": [
                            "Không được dùng thuộc tính riêng của gian hàng khác"
                        ]
                    },
                    http_status=403,
                )

        values_by_attribute: dict = defaultdict(list)
        attributes_by_id = {}
        for value in values:
            values_by_attribute[value.attribute_id].append(value)
            attributes_by_id[value.attribute_id] = value.attribute
        ordered_attribute_ids = sorted(
            values_by_attribute,
            key=lambda attribute_id: (
                attributes_by_id[attribute_id].sort_order,
                attributes_by_id[attribute_id].name,
                str(attribute_id),
            ),
        )
        combinations = list(
            cartesian_product(
                *(values_by_attribute[attribute_id] for attribute_id in ordered_attribute_ids)
            )
        )

        ProductAttributeValue.objects.bulk_create(
            [
                ProductAttributeValue(
                    product=locked_product,
                    attribute_value=value,
                )
                for value in values
            ],
            ignore_conflicts=True,
        )
        reserved_skus: set[str] = set()
        variants: list[ProductVariant] = []
        for combination in combinations:
            sku = VariantService._generate_sku(
                product=locked_product,
                reserved_skus=reserved_skus,
            )
            reserved_skus.add(sku)
            variants.append(
                ProductVariant(
                    product=locked_product,
                    shop=locked_product.shop,
                    sku=sku,
                    name=" / ".join(value.display_value or value.value for value in combination),
                    original_price=Decimal("0"),
                    sale_price=Decimal("0"),
                )
            )
        try:
            ProductVariant.objects.bulk_create(variants)
            from apps.inventory.models import InventoryBalance

            InventoryBalance.objects.bulk_create(
                [InventoryBalance(variant=variant) for variant in variants],
                ignore_conflicts=True,
            )
            VariantAttributeValue.objects.bulk_create(
                [
                    VariantAttributeValue(
                        variant=variant,
                        attribute=value.attribute,
                        attribute_value=value,
                    )
                    for variant, combination in zip(variants, combinations, strict=True)
                    for value in combination
                ]
            )
        except IntegrityError as exc:
            raise BusinessError(
                "Không thể tạo tổ hợp biến thể",
                errors={
                    "variants": ["Tổ hợp thuộc tính hoặc SKU bị trùng; vui lòng tải lại và thử lại"]
                },
            ) from exc
        ProductService.update_price_cache(product=locked_product)
        return variants

    @staticmethod
    def _decimal_value(value, *, field: str, nullable: bool = False):
        if value in (None, ""):
            if nullable:
                return None
            raise BusinessError(
                "Giá không hợp lệ",
                errors={field: ["Trường này không được để trống"]},
            )
        try:
            normalized = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise BusinessError(
                "Giá không hợp lệ",
                errors={field: ["Giá phải là một số hợp lệ"]},
            ) from exc
        if not normalized.is_finite() or normalized < 0:
            raise BusinessError(
                "Giá không hợp lệ",
                errors={field: ["Giá phải là số không âm"]},
            )
        return normalized

    @staticmethod
    @transaction.atomic
    def update_variant(
        *,
        variant: ProductVariant,
        seller_user,
        data: dict,
    ) -> ProductVariant:
        shop = _get_seller_shop(seller_user)
        locked_variant = (
            ProductVariant.objects.select_for_update()
            .select_related("product", "shop")
            .filter(
                pk=variant.pk,
                product__shop_id=shop.pk,
                is_deleted=False,
                product__is_deleted=False,
            )
            .first()
        )
        if locked_variant is None:
            raise BusinessError(
                "Bạn không có quyền thao tác biến thể này",
                errors={"variant": ["Biến thể không thuộc gian hàng của bạn"]},
                http_status=403,
            )
        VariantService.validate_shop_consistency(
            product=locked_variant.product,
            shop=locked_variant.shop,
        )
        if locked_variant.product.status not in ProductService.EDITABLE_STATUSES:
            raise BusinessError(
                "Không thể sửa biến thể ở trạng thái hiện tại",
                errors={"status": ["Sản phẩm phải ở trạng thái nháp hoặc bị từ chối"]},
            )
        if "stock_quantity" in data or "available_stock" in data:
            raise BusinessError(
                "Tồn kho chỉ được thay đổi qua module Kho",
                errors={
                    "stock_quantity": [
                        "Hãy tạo phiếu nhập, xuất hoặc kiểm kê để giữ đầy đủ lịch sử"
                    ]
                },
            )

        allowed_fields = {
            "sku",
            "barcode",
            "name",
            "original_price",
            "sale_price",
            "cost_price",
            "weight_grams",
            "is_active",
        }
        updates = {key: value for key, value in data.items() if key in allowed_fields}
        if "sku" in updates:
            updates["sku"] = str(updates["sku"]).strip()
            if not updates["sku"]:
                updates["sku"] = VariantService._generate_sku(product=locked_variant.product)
        if "barcode" in updates:
            raw_barcode = updates["barcode"]
            updates["barcode"] = str(raw_barcode).strip() if raw_barcode not in (None, "") else None
            if updates["barcode"] and any(
                ord(character) < 32 or ord(character) > 126 for character in updates["barcode"]
            ):
                raise BusinessError(
                    "Barcode không hợp lệ",
                    errors={"barcode": ["Barcode chỉ được chứa ký tự ASCII in được"]},
                )
        for field in ("original_price", "sale_price"):
            if field in updates:
                updates[field] = VariantService._decimal_value(
                    updates[field],
                    field=field,
                )
        if "cost_price" in updates:
            updates["cost_price"] = VariantService._decimal_value(
                updates["cost_price"],
                field="cost_price",
                nullable=True,
            )
        original_price = updates.get("original_price", locked_variant.original_price)
        sale_price = updates.get("sale_price", locked_variant.sale_price)
        if original_price != 0 and sale_price > original_price:
            raise BusinessError(
                "Giá bán không được lớn hơn giá gốc",
                errors={"sale_price": ["Giá bán phải nhỏ hơn hoặc bằng giá gốc"]},
            )
        if "weight_grams" in updates:
            try:
                weight = int(updates["weight_grams"])
            except (TypeError, ValueError) as exc:
                raise BusinessError(
                    "Khối lượng không hợp lệ",
                    errors={"weight_grams": ["Khối lượng phải là số nguyên dương"]},
                ) from exc
            if weight <= 0:
                raise BusinessError(
                    "Khối lượng không hợp lệ",
                    errors={"weight_grams": ["Khối lượng phải lớn hơn 0"]},
                )
            updates["weight_grams"] = weight

        sku = updates.get("sku", locked_variant.sku)
        if (
            ProductVariant.objects.filter(
                shop_id=locked_variant.shop_id,
                sku=sku,
            )
            .exclude(pk=locked_variant.pk)
            .exists()
        ):
            raise BusinessError(
                "SKU đã tồn tại trong gian hàng",
                errors={"sku": ["Vui lòng sử dụng SKU khác"]},
            )
        barcode = updates.get("barcode", locked_variant.barcode)
        if (
            barcode
            and ProductVariant.objects.filter(
                shop_id=locked_variant.shop_id,
                barcode=barcode,
            )
            .exclude(pk=locked_variant.pk)
            .exists()
        ):
            raise BusinessError(
                "Barcode đã tồn tại trong gian hàng",
                errors={"barcode": ["Vui lòng sử dụng barcode khác"]},
            )

        for field, value in updates.items():
            setattr(locked_variant, field, value)
        if updates:
            try:
                locked_variant.save(update_fields=(*updates.keys(), "updated_at"))
            except IntegrityError as exc:
                raise BusinessError(
                    "Không thể cập nhật biến thể do dữ liệu bị trùng hoặc không hợp lệ",
                    errors={"variant": ["Vui lòng kiểm tra SKU, barcode và giá"]},
                ) from exc
            ProductService.update_price_cache(product=locked_variant.product)
        return locked_variant


# Backwards-compatible name retained for code written during the model task.
ProductVariantService = VariantService
