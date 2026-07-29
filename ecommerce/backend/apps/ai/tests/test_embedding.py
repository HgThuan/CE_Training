from unittest.mock import call, patch

import pytest
from django.conf import settings
from django.test import override_settings

from apps.ai.embedding_service import EmbeddingService
from apps.ai.models import EMBEDDING_DIMENSIONS, ProductEmbedding
from apps.ai.services import AIService, EmbeddingResult
from apps.ai.tasks import index_product_embedding, reindex_all_products
from apps.catalog.tests.factories import BrandFactory, CategoryFactory
from apps.product.models import Product, ProductAttributeValue
from apps.product.tests.factories import (
    AttributeFactory,
    AttributeValueFactory,
    ProductFactory,
)


def embedding_result(value: float = 0.01) -> EmbeddingResult:
    return EmbeddingResult(
        vector=[value] * EMBEDDING_DIMENSIONS,
        ai_used=True,
        fallback_used=False,
        cached=False,
        model_name=settings.AI_EMBEDDING_MODEL,
    )


@pytest.mark.django_db
def test_source_text_and_hash_are_deterministic():
    product = ProductFactory(
        status=Product.Status.APPROVED,
        name="Điện thoại bền",
        description="<p>Chống nước tốt</p>",
    )
    attribute = AttributeFactory(name="Màu sắc")
    value = AttributeValueFactory(
        attribute=attribute,
        value="den",
        display_value="Đen",
    )
    ProductAttributeValue.objects.create(
        product=product,
        attribute_value=value,
    )
    product = (
        Product.objects.select_related("category", "brand")
        .prefetch_related("product_attribute_links__attribute_value__attribute")
        .get(pk=product.pk)
    )

    first_source = EmbeddingService.build_source_text(product)
    second_source = EmbeddingService.build_source_text(product)

    assert first_source == second_source
    assert "<p>" not in first_source
    assert "Màu sắc: Đen" in first_source
    assert EmbeddingService.content_hash(first_source) == EmbeddingService.content_hash(
        second_source
    )


@pytest.mark.django_db
def test_index_product_saves_vector_and_skips_unchanged_content():
    product = ProductFactory(
        status=Product.Status.APPROVED,
        name="Laptop AI",
        description="Máy tính cho công việc.",
    )
    result = embedding_result()

    with (
        patch.object(EmbeddingService, "is_enabled", return_value=True),
        patch.object(AIService, "get_embedding", return_value=result) as get_embedding,
    ):
        indexed = EmbeddingService.index_product(product.pk)
        unchanged = EmbeddingService.index_product(product.pk)

    assert indexed.status == "indexed"
    assert unchanged.status == "unchanged"
    assert get_embedding.call_count == 1
    stored = ProductEmbedding.objects.get(product=product)
    assert list(stored.embedding) == result.vector
    assert stored.content_hash == indexed.content_hash
    assert stored.source_text.startswith("Tên sản phẩm: Laptop AI")


@pytest.mark.django_db
def test_reindex_replaces_stale_embedding_after_content_change():
    product = ProductFactory(
        status=Product.Status.APPROVED,
        name="Tai nghe",
        description="Phiên bản đầu.",
    )
    with (
        patch.object(EmbeddingService, "is_enabled", return_value=True),
        patch.object(
            AIService,
            "get_embedding",
            side_effect=[embedding_result(0.01), embedding_result(0.02)],
        ),
    ):
        first = EmbeddingService.index_product(product.pk)
        product.description = "Phiên bản đã cập nhật."
        product.save(update_fields=("description", "updated_at"))
        second = EmbeddingService.index_product(product.pk)

    assert first.content_hash != second.content_hash
    assert ProductEmbedding.objects.filter(product=product).count() == 1
    assert ProductEmbedding.objects.get(product=product).content_hash == second.content_hash


@pytest.mark.django_db
def test_non_public_product_removes_stale_embedding_without_provider_call():
    product = ProductFactory(status=Product.Status.APPROVED)
    with (
        patch.object(EmbeddingService, "is_enabled", return_value=True),
        patch.object(AIService, "get_embedding", return_value=embedding_result()),
    ):
        EmbeddingService.index_product(product.pk)
    product.status = Product.Status.HIDDEN
    product.save(update_fields=("status", "updated_at"))

    with (
        patch.object(EmbeddingService, "is_enabled", return_value=True),
        patch.object(AIService, "get_embedding") as get_embedding,
    ):
        result = EmbeddingService.index_product(product.pk)

    assert result.status == "removed"
    assert not ProductEmbedding.objects.filter(product=product).exists()
    get_embedding.assert_not_called()


@pytest.mark.django_db
def test_queued_task_does_not_call_provider_after_feature_is_disabled():
    product = ProductFactory(status=Product.Status.APPROVED)

    with (
        patch.object(EmbeddingService, "is_enabled", return_value=False),
        patch.object(AIService, "get_embedding") as get_embedding,
    ):
        result = index_product_embedding.run(str(product.pk))
        bulk_result = reindex_all_products.run()

    assert result["status"] == "disabled"
    assert bulk_result == {"status": "disabled", "enqueued": 0}
    get_embedding.assert_not_called()


@pytest.mark.django_db
def test_index_product_rejects_non_finite_provider_vector():
    product = ProductFactory(status=Product.Status.APPROVED)
    invalid = EmbeddingResult(
        vector=[float("nan"), *([0.01] * (EMBEDDING_DIMENSIONS - 1))],
        ai_used=True,
        fallback_used=False,
        cached=False,
        model_name=settings.AI_EMBEDDING_MODEL,
    )

    with (
        patch.object(EmbeddingService, "is_enabled", return_value=True),
        patch.object(AIService, "get_embedding", return_value=invalid),
    ):
        result = EmbeddingService.index_product(product.pk)

    assert result.status == "unavailable"
    assert not ProductEmbedding.objects.filter(product=product).exists()


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True)
def test_product_signal_dispatches_only_when_feature_and_provider_are_ready(
    django_capture_on_commit_callbacks,
):
    with (
        patch("apps.ai.signals.AIService.is_configured", return_value=True),
        patch("apps.ai.signals.SiteSetting.get_bool", return_value=True),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        product = ProductFactory(status=Product.Status.APPROVED)

    delay.assert_called_once_with(str(product.pk))

    with (
        patch("apps.ai.signals.AIService.is_configured", return_value=True),
        patch("apps.ai.signals.SiteSetting.get_bool", return_value=False),
        patch("apps.ai.signals.index_product_embedding.delay") as disabled_delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        ProductFactory(status=Product.Status.APPROVED)

    disabled_delay.assert_not_called()


@pytest.mark.django_db
def test_attribute_link_create_update_and_delete_reindex_product(
    django_capture_on_commit_callbacks,
):
    product = ProductFactory(status=Product.Status.APPROVED)
    attribute = AttributeFactory()
    first_value = AttributeValueFactory(attribute=attribute)
    second_value = AttributeValueFactory(attribute=attribute)

    with (
        patch(
            "apps.ai.signals._embedding_indexing_enabled",
            return_value=True,
        ),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        link = ProductAttributeValue.objects.create(
            product=product,
            attribute_value=first_value,
        )

    delay.assert_called_once_with(str(product.pk))

    with (
        patch(
            "apps.ai.signals._embedding_indexing_enabled",
            return_value=True,
        ),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        link.attribute_value = second_value
        link.save(update_fields=("attribute_value", "updated_at"))

    delay.assert_called_once_with(str(product.pk))

    with (
        patch(
            "apps.ai.signals._embedding_indexing_enabled",
            return_value=True,
        ),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        link.delete()

    delay.assert_called_once_with(str(product.pk))


@pytest.mark.django_db
def test_category_rename_reindexes_only_approved_public_products(
    django_capture_on_commit_callbacks,
):
    category = CategoryFactory()
    first_product = ProductFactory(
        category=category,
        status=Product.Status.APPROVED,
    )
    second_product = ProductFactory(
        category=category,
        status=Product.Status.APPROVED,
    )
    ProductFactory(category=category, status=Product.Status.DRAFT)
    ProductFactory(
        category=category,
        status=Product.Status.APPROVED,
        is_deleted=True,
    )
    locked_shop_product = ProductFactory(
        category=category,
        status=Product.Status.APPROVED,
    )
    locked_shop_product.shop.is_deleted = True
    locked_shop_product.shop.save(update_fields=("is_deleted", "updated_at"))

    with (
        patch(
            "apps.ai.signals._embedding_indexing_enabled",
            return_value=True,
        ),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        category.name = "Danh mục đã đổi tên"
        category.save(update_fields=("name", "updated_at"))

    assert delay.call_count == 2
    delay.assert_has_calls(
        [
            call(str(first_product.pk)),
            call(str(second_product.pk)),
        ],
        any_order=True,
    )


@pytest.mark.django_db
def test_brand_rename_reindexes_only_approved_public_products(
    django_capture_on_commit_callbacks,
):
    brand = BrandFactory()
    first_product = ProductFactory(
        brand=brand,
        status=Product.Status.APPROVED,
    )
    second_product = ProductFactory(
        brand=brand,
        status=Product.Status.APPROVED,
    )
    ProductFactory(brand=brand, status=Product.Status.HIDDEN)
    ProductFactory(
        brand=brand,
        status=Product.Status.APPROVED,
        is_deleted=True,
    )

    with (
        patch(
            "apps.ai.signals._embedding_indexing_enabled",
            return_value=True,
        ),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        brand.name = "Thương hiệu đã đổi tên"
        brand.save(update_fields=("name", "updated_at"))

    assert delay.call_count == 2
    delay.assert_has_calls(
        [
            call(str(first_product.pk)),
            call(str(second_product.pk)),
        ],
        any_order=True,
    )


@pytest.mark.django_db
def test_attribute_source_changes_reindex_each_affected_product_once(
    django_capture_on_commit_callbacks,
):
    attribute = AttributeFactory()
    value = AttributeValueFactory(attribute=attribute)
    product = ProductFactory(status=Product.Status.APPROVED)
    ProductAttributeValue.objects.create(product=product, attribute_value=value)

    with (
        patch(
            "apps.ai.signals._embedding_indexing_enabled",
            return_value=True,
        ),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        value.display_value = "Giá trị hiển thị mới"
        value.save(update_fields=("display_value", "updated_at"))

    delay.assert_called_once_with(str(product.pk))

    with (
        patch(
            "apps.ai.signals._embedding_indexing_enabled",
            return_value=True,
        ),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        attribute.name = "Thuộc tính mới"
        attribute.save(update_fields=("name", "updated_at"))

    delay.assert_called_once_with(str(product.pk))


@pytest.mark.django_db
def test_related_source_signals_do_not_enqueue_when_ai_is_disabled(
    django_capture_on_commit_callbacks,
):
    category = CategoryFactory()
    brand = BrandFactory()
    product = ProductFactory(
        category=category,
        brand=brand,
        status=Product.Status.APPROVED,
    )
    value = AttributeValueFactory()

    with (
        patch(
            "apps.ai.signals._embedding_indexing_enabled",
            return_value=False,
        ),
        patch("apps.ai.signals.index_product_embedding.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        ProductAttributeValue.objects.create(
            product=product,
            attribute_value=value,
        )
        category.name = "Danh mục không enqueue"
        category.save(update_fields=("name", "updated_at"))
        brand.name = "Thương hiệu không enqueue"
        brand.save(update_fields=("name", "updated_at"))

    delay.assert_not_called()
