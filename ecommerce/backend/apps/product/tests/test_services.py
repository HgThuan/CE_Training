"""Unit tests for product services, selectors, and state transitions."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from apps.account.models import Shop, User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.catalog.tests.factories import CategoryFactory
from apps.common.exceptions import BusinessError
from apps.common.models import AuditLog
from apps.product.models import Product, ProductMedia
from apps.product.selectors import ProductSelector
from apps.product.services import (
    MediaService,
    ProductService,
    VariantService,
    _lock_owned_product,
)
from apps.product.state_machine import ProductStateMachine
from apps.product.tests.factories import (
    AttributeFactory,
    AttributeValueFactory,
    ProductFactory,
    ProductMediaFactory,
    ProductVariantFactory,
)


def image_upload(name: str = "image.jpg") -> SimpleUploadedFile:
    output = BytesIO()
    Image.new("RGB", (32, 32), color="red").save(output, format="JPEG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/jpeg")


def mp4_upload(name: str = "video.bin") -> SimpleUploadedFile:
    content = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2"
    return SimpleUploadedFile(name, content, content_type="application/octet-stream")


def test_state_machine_defines_only_documented_transitions():
    assert ProductStateMachine.TRANSITIONS == {
        Product.Status.DRAFT: {Product.Status.PENDING_REVIEW},
        Product.Status.PENDING_REVIEW: {
            Product.Status.APPROVED,
            Product.Status.REJECTED,
        },
        Product.Status.REJECTED: {Product.Status.DRAFT},
        Product.Status.APPROVED: {
            Product.Status.HIDDEN,
            Product.Status.SUSPENDED,
        },
        Product.Status.HIDDEN: {Product.Status.APPROVED},
        Product.Status.SUSPENDED: {Product.Status.APPROVED},
    }
    assert ProductStateMachine.DELETABLE_STATUSES == {
        Product.Status.DRAFT,
        Product.Status.HIDDEN,
    }


@pytest.mark.django_db
def test_owned_product_lock_targets_only_product_table(monkeypatch):
    product = ProductFactory()
    manager = Product.objects
    original_select_for_update = manager.select_for_update
    captured_options = {}

    def capture_select_for_update(*args, **kwargs):
        captured_options.update(kwargs)
        return original_select_for_update(*args, **kwargs)

    monkeypatch.setattr(manager, "select_for_update", capture_select_for_update)

    locked_product, _shop = _lock_owned_product(
        seller_user=product.shop.owner,
        product_id=product.pk,
    )

    assert locked_product.pk == product.pk
    assert captured_options["of"] == ("self",)


@pytest.mark.django_db
def test_state_machine_allows_owner_submit_and_writes_uuid_audit_log():
    product = ProductFactory()

    transitioned = ProductStateMachine.transition(
        product,
        Product.Status.PENDING_REVIEW,
        actor=product.shop.owner,
        request_id="request-product-1",
    )

    assert transitioned.status == Product.Status.PENDING_REVIEW
    assert AuditLog.objects.filter(
        action="submit_product_review",
        target_type="Product",
        target_id=str(product.pk),
        request_id="request-product-1",
    ).exists()


@pytest.mark.django_db
def test_state_machine_rejects_invalid_transition_and_cross_shop_seller():
    product = ProductFactory()
    other_seller = ShopFactory().owner

    with pytest.raises(BusinessError, match="quyền"):
        ProductStateMachine.transition(
            product,
            Product.Status.PENDING_REVIEW,
            actor=other_seller,
        )
    with pytest.raises(BusinessError, match="Không thể chuyển"):
        ProductStateMachine.transition(
            product,
            Product.Status.APPROVED,
            actor=UserFactory(role=User.Role.ADMIN),
        )


@pytest.mark.django_db
def test_admin_rejection_requires_reason_and_sets_rejection_reason():
    product = ProductFactory(status=Product.Status.PENDING_REVIEW)
    admin = UserFactory(role=User.Role.ADMIN)

    with pytest.raises(BusinessError, match="Lý do"):
        ProductService.admin_reject(
            product=product,
            admin_user=admin,
            reason=" ",
        )

    rejected = ProductService.admin_reject(
        product=product,
        admin_user=admin,
        reason="Thiếu ảnh mô tả",
    )
    assert rejected.status == Product.Status.REJECTED
    assert rejected.rejection_reason == "Thiếu ảnh mô tả"


@pytest.mark.django_db
def test_state_machine_supports_hide_unhide_suspend_and_restore():
    product = ProductFactory(status=Product.Status.PENDING_REVIEW)
    ProductVariantFactory(product=product, shop=product.shop)
    admin = UserFactory(role=User.Role.ADMIN)

    product = ProductStateMachine.transition(
        product,
        Product.Status.APPROVED,
        actor=admin,
    )
    product = ProductStateMachine.transition(
        product,
        Product.Status.HIDDEN,
        actor=admin,
    )
    product = ProductStateMachine.transition(
        product,
        Product.Status.APPROVED,
        actor=admin,
    )
    product = ProductStateMachine.transition(
        product,
        Product.Status.SUSPENDED,
        actor=admin,
    )
    product = ProductStateMachine.transition(
        product,
        Product.Status.APPROVED,
        actor=admin,
    )

    assert product.status == Product.Status.APPROVED
    assert AuditLog.objects.filter(target_id=str(product.pk)).count() == 5


@pytest.mark.django_db
def test_create_product_derives_shop_from_seller_and_sanitizes_description():
    seller_shop = ShopFactory()
    forged_shop = ShopFactory()
    category = CategoryFactory()

    created = ProductService.create_product(
        seller_user=seller_shop.owner,
        data={
            "shop": forged_shop,
            "shop_id": forged_shop.pk,
            "category": category,
            "name": "  Áo sơ mi  ",
            "description": '<p>Đẹp <script>alert(1)</script><a href="javascript:x">x</a></p>',
        },
    )

    assert created.shop_id == seller_shop.pk
    assert created.status == Product.Status.DRAFT
    assert created.slug == "ao-so-mi"
    assert "<script>" not in created.description
    assert "javascript:" not in created.description
    assert "<p>" in created.description


@pytest.mark.django_db
def test_create_product_rechecks_catalog_state_from_database():
    shop = ShopFactory()
    category = CategoryFactory(is_active=False, is_deleted=True)
    category.is_active = True
    category.is_deleted = False

    with pytest.raises(BusinessError, match="Danh mục"):
        ProductService.create_product(
            seller_user=shop.owner,
            data={"category": category, "name": "Danh mục giả mạo"},
        )


@pytest.mark.django_db
def test_create_product_requires_operational_shop():
    shop = ShopFactory(status=Shop.Status.LOCKED)

    with pytest.raises(BusinessError, match="khóa"):
        ProductService.create_product(
            seller_user=shop.owner,
            data={"category": CategoryFactory(), "name": "Không thể tạo"},
        )


@pytest.mark.django_db
def test_update_product_blocks_cross_shop_and_returns_rejected_product_to_draft():
    product = ProductFactory(status=Product.Status.REJECTED)

    with pytest.raises(BusinessError, match="quyền"):
        ProductService.update_product(
            product=product,
            seller_user=ShopFactory().owner,
            data={"name": "Chiếm quyền"},
        )

    updated = ProductService.update_product(
        product=product,
        seller_user=product.shop.owner,
        data={"name": "Tên đã sửa"},
    )
    assert updated.name == "Tên đã sửa"
    assert updated.status == Product.Status.DRAFT
    assert updated.rejection_reason is None


@pytest.mark.django_db
def test_update_product_does_not_trust_in_memory_shop_id():
    victim_product = ProductFactory()
    attacker_shop = ShopFactory()
    victim_product.shop = attacker_shop

    with pytest.raises(BusinessError, match="quyền"):
        ProductService.update_product(
            product=victim_product,
            seller_user=attacker_shop.owner,
            data={"name": "Forged ownership"},
        )

    victim_product.refresh_from_db()
    assert victim_product.name != "Forged ownership"


@pytest.mark.django_db
def test_soft_delete_only_allows_draft_or_hidden_and_checks_ownership():
    draft = ProductFactory()
    deleted = ProductService.soft_delete_product(
        product=draft,
        seller_user=draft.shop.owner,
    )
    assert deleted.is_deleted is True
    assert deleted.deleted_at is not None

    approved = ProductFactory(status=Product.Status.APPROVED)
    with pytest.raises(BusinessError, match="trạng thái"):
        ProductService.soft_delete_product(
            product=approved,
            seller_user=approved.shop.owner,
        )


@pytest.mark.django_db
def test_submit_requires_available_sku_then_transitions():
    product = ProductFactory()

    with pytest.raises(BusinessError, match="SKU"):
        ProductService.submit_for_review(
            product=product,
            actor=product.shop.owner,
        )

    ProductVariantFactory(product=product, shop=product.shop)
    submitted = ProductService.submit_for_review(
        product=product,
        actor=product.shop.owner,
    )
    assert submitted.status == Product.Status.PENDING_REVIEW


@pytest.mark.django_db
def test_admin_approve_and_hide_set_metadata_and_audit():
    product = ProductFactory(status=Product.Status.PENDING_REVIEW)
    ProductVariantFactory(product=product, shop=product.shop)
    admin = UserFactory(role=User.Role.ADMIN)

    approved = ProductService.admin_approve(
        product=product,
        admin_user=admin,
        request_id="approve-request",
    )
    assert approved.status == Product.Status.APPROVED
    assert approved.approved_by_id == admin.pk
    assert approved.approved_at is not None

    hidden = ProductService.admin_hide(
        product=approved,
        admin_user=admin,
        request_id="hide-request",
    )
    assert hidden.status == Product.Status.HIDDEN
    assert (
        AuditLog.objects.filter(
            actor=admin,
            target_id=str(product.pk),
        ).count()
        == 2
    )
    assert AuditLog.objects.filter(
        actor=admin,
        target_id=str(product.pk),
        action="approve_product",
    ).exists()
    assert AuditLog.objects.filter(
        actor=admin,
        target_id=str(product.pk),
        action="hide_product",
    ).exists()


@pytest.mark.django_db
def test_price_cache_uses_only_active_non_deleted_variants():
    product = ProductFactory()
    ProductVariantFactory(
        product=product,
        shop=product.shop,
        sale_price=100,
    )
    ProductVariantFactory(
        product=product,
        shop=product.shop,
        sale_price=300,
    )
    ProductVariantFactory(
        product=product,
        shop=product.shop,
        sale_price=1,
        is_active=False,
    )

    cached = ProductService.update_price_cache(product=product)
    assert cached.min_price == 100
    assert cached.max_price == 300


@pytest.mark.django_db
@override_settings(MAX_IMAGE_UPLOAD_MB=1)
def test_media_rejects_spoofed_image_content():
    product = ProductFactory()
    fake_image = SimpleUploadedFile(
        "forged.jpg",
        b"this is not an image",
        content_type="image/jpeg",
    )

    with pytest.raises(BusinessError, match="Nội dung"):
        MediaService.upload_media(
            product=product,
            uploaded_file=fake_image,
            media_type=ProductMedia.MediaType.IMAGE,
            seller_user=product.shop.owner,
        )


@pytest.mark.django_db
@override_settings(MAX_IMAGE_UPLOAD_MB=1, MEDIA_URL="/media/")
def test_media_upload_reorder_primary_and_delete(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    product = ProductFactory()
    first = MediaService.upload_media(
        product=product,
        uploaded_file=image_upload("first.jpg"),
        media_type=ProductMedia.MediaType.IMAGE,
        seller_user=product.shop.owner,
    )
    second = MediaService.upload_media(
        product=product,
        uploaded_file=image_upload("second.jpg"),
        media_type=ProductMedia.MediaType.IMAGE,
        seller_user=product.shop.owner,
    )

    ordered = MediaService.reorder_media(
        product=product,
        ordered_ids=[second.pk, first.pk],
        seller_user=product.shop.owner,
    )
    assert [item.pk for item in ordered] == [second.pk, first.pk]
    assert [item.sort_order for item in ordered] == [0, 1]

    primary = MediaService.set_primary(
        product=product,
        media_id=second.pk,
        seller_user=product.shop.owner,
    )
    assert primary.is_primary is True

    MediaService.delete_media(media=first, seller_user=product.shop.owner)
    assert not ProductMedia.objects.filter(pk=first.pk).exists()


@pytest.mark.django_db
@override_settings(MAX_VIDEO_UPLOAD_MB=1, MEDIA_URL="/media/")
def test_video_uses_magic_bytes_and_enforces_one_video_limit(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    product = ProductFactory()

    video = MediaService.upload_media(
        product=product,
        uploaded_file=mp4_upload(),
        media_type=ProductMedia.MediaType.VIDEO,
        seller_user=product.shop.owner,
    )
    assert video.file_url.endswith(".mp4")

    with pytest.raises(BusinessError, match="giới hạn"):
        MediaService.upload_media(
            product=product,
            uploaded_file=mp4_upload("second.mp4"),
            media_type=ProductMedia.MediaType.VIDEO,
            seller_user=product.shop.owner,
        )


@pytest.mark.django_db
@override_settings(MAX_IMAGE_UPLOAD_MB=1)
def test_media_limits_nine_images_and_blocks_foreign_reorder():
    product = ProductFactory()
    for index in range(9):
        ProductMediaFactory(product=product, sort_order=index)

    with pytest.raises(BusinessError, match="giới hạn"):
        MediaService.upload_media(
            product=product,
            uploaded_file=image_upload(),
            media_type=ProductMedia.MediaType.IMAGE,
            seller_user=product.shop.owner,
        )

    foreign_media = ProductMediaFactory()
    with pytest.raises(BusinessError, match="không khớp"):
        MediaService.reorder_media(
            product=product,
            ordered_ids=[
                *product.media.values_list("pk", flat=True),
                foreign_media.pk,
            ],
            seller_user=product.shop.owner,
        )


@pytest.mark.django_db
def test_generate_variants_builds_cartesian_product_and_auto_sku():
    product = ProductFactory()
    color = AttributeFactory(shop=product.shop, name="Màu", code="color")
    size = AttributeFactory(shop=product.shop, name="Size", code="size")
    red = AttributeValueFactory(attribute=color, value="Đỏ")
    blue = AttributeValueFactory(attribute=color, value="Xanh")
    small = AttributeValueFactory(attribute=size, value="S")
    medium = AttributeValueFactory(attribute=size, value="M")

    variants = VariantService.generate_variants(
        product=product,
        attribute_value_ids=[red.pk, blue.pk, small.pk, medium.pk],
        seller_user=product.shop.owner,
    )

    assert len(variants) == 4
    assert len({variant.sku for variant in variants}) == 4
    assert all(variant.shop_id == product.shop_id for variant in variants)
    assert all(variant.variant_attribute_links.count() == 2 for variant in variants)
    assert product.product_attribute_links.count() == 4


@pytest.mark.django_db
def test_generate_variants_rejects_attribute_from_another_shop():
    product = ProductFactory()
    foreign_attribute = AttributeFactory(shop=ShopFactory())
    foreign_value = AttributeValueFactory(attribute=foreign_attribute)

    with pytest.raises(BusinessError, match="không thuộc"):
        VariantService.generate_variants(
            product=product,
            attribute_value_ids=[foreign_value.pk],
            seller_user=product.shop.owner,
        )


@pytest.mark.django_db
def test_update_variant_validates_prices_uniqueness_and_refreshes_cache():
    variant = ProductVariantFactory()
    ProductVariantFactory(
        product=variant.product,
        shop=variant.shop,
        sku="TAKEN-SKU",
    )

    with pytest.raises(BusinessError, match="Giá bán"):
        VariantService.update_variant(
            variant=variant,
            seller_user=variant.shop.owner,
            data={"original_price": 100, "sale_price": 101},
        )
    with pytest.raises(BusinessError, match="SKU"):
        VariantService.update_variant(
            variant=variant,
            seller_user=variant.shop.owner,
            data={"sku": "TAKEN-SKU"},
        )
    updated = VariantService.update_variant(
        variant=variant,
        seller_user=variant.shop.owner,
        data={
            "sku": "",
            "barcode": None,
            "original_price": 500,
            "sale_price": 400,
            "stock_quantity": 12,
        },
    )
    updated.product.refresh_from_db()
    assert updated.sku
    assert updated.barcode is None
    assert updated.sale_price == 400
    assert updated.stock_quantity == 12
    assert updated.product.min_price == 400


@pytest.mark.django_db
def test_selector_isolates_sellers_and_filters_public_products():
    public_product = ProductFactory(status=Product.Status.APPROVED)
    seller_private = ProductFactory(shop=public_product.shop, status=Product.Status.DRAFT)
    other_product = ProductFactory(status=Product.Status.APPROVED)

    seller_ids = set(
        ProductSelector.for_seller(public_product.shop.owner).values_list(
            "pk",
            flat=True,
        )
    )
    assert seller_ids == {public_product.pk, seller_private.pk}
    assert other_product.pk not in seller_ids

    public_ids = set(ProductSelector.public_queryset().values_list("pk", flat=True))
    assert public_product.pk in public_ids
    assert seller_private.pk not in public_ids

    public_product.shop.status = Shop.Status.LOCKED
    public_product.shop.save(update_fields=("status", "updated_at"))
    assert public_product.pk not in set(
        ProductSelector.public_queryset().values_list("pk", flat=True)
    )


@pytest.mark.django_db
def test_detail_slug_requires_shop_when_slug_exists_in_multiple_shops():
    first = ProductFactory(slug="same-product-slug")
    second = ProductFactory(slug="same-product-slug")

    with pytest.raises(BusinessError, match="scope"):
        ProductSelector.detail_with_relations("same-product-slug")

    detail = ProductSelector.detail_with_relations(
        "same-product-slug",
        shop=second.shop,
    )
    assert detail.pk == second.pk
    assert ProductSelector.detail_with_relations(first.pk).pk == first.pk


@pytest.mark.django_db
def test_non_admin_cannot_approve_product():
    product = ProductFactory(status=Product.Status.PENDING_REVIEW)
    ProductVariantFactory(product=product, shop=product.shop)

    with pytest.raises(BusinessError, match="Admin"):
        ProductService.admin_approve(
            product=product,
            admin_user=product.shop.owner,
        )


@pytest.mark.django_db
def test_media_cross_shop_owner_is_forbidden():
    product = ProductFactory()

    with pytest.raises(BusinessError, match="quyền"):
        MediaService.upload_media(
            product=product,
            uploaded_file=image_upload(),
            media_type=ProductMedia.MediaType.IMAGE,
            seller_user=ShopFactory().owner,
        )


@pytest.mark.django_db
def test_update_variant_cross_shop_owner_is_forbidden():
    variant = ProductVariantFactory()

    with pytest.raises(BusinessError, match="quyền"):
        VariantService.update_variant(
            variant=variant,
            seller_user=ShopFactory().owner,
            data={"sale_price": 100},
        )
