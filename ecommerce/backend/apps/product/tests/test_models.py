from decimal import Decimal
from uuid import UUID

import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.account.tests.factories import ShopFactory
from apps.catalog.services import CategoryService
from apps.common.exceptions import BusinessError
from apps.product.models import (
    Product,
    ProductAttributeValue,
    ProductMedia,
    VariantAttributeValue,
)
from apps.product.services import ProductVariantService
from apps.product.tests.factories import (
    AttributeFactory,
    AttributeValueFactory,
    ProductFactory,
    ProductMediaFactory,
    ProductVariantFactory,
)


@pytest.mark.django_db
def test_product_defaults_uuid_and_timestamps():
    product = ProductFactory()

    assert isinstance(product.pk, UUID)
    assert product.status == Product.Status.DRAFT
    assert product.rating_average == Decimal("0")
    assert product.rating_count == 0
    assert product.sold_count == 0
    assert product.created_at is not None
    assert product.updated_at is not None


@pytest.mark.django_db
def test_product_slug_is_unique_per_shop_only_while_not_deleted():
    product = ProductFactory(slug="same-slug")

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductFactory(shop=product.shop, slug="same-slug")

    Product.objects.filter(pk=product.pk).update(is_deleted=True)
    replacement = ProductFactory(shop=product.shop, slug="same-slug")
    other_shop_product = ProductFactory(slug="same-slug")

    assert replacement.pk != product.pk
    assert other_shop_product.shop_id != product.shop_id


@pytest.mark.django_db
def test_product_protects_category_from_hard_and_soft_delete():
    product = ProductFactory()

    with pytest.raises(ProtectedError):
        product.category.delete()
    with pytest.raises(BusinessError, match="sản phẩm"):
        CategoryService.soft_delete(category=product.category)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        {"min_price": Decimal("-1")},
        {"max_price": Decimal("-1")},
        {"min_price": Decimal("200"), "max_price": Decimal("100")},
        {"rating_average": Decimal("5.01")},
    ],
)
def test_product_price_and_rating_constraints(overrides):
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductFactory(**overrides)


@pytest.mark.django_db
def test_product_allows_nullable_or_valid_price_cache():
    no_cache = ProductFactory(min_price=None, max_price=None)
    cached = ProductFactory(min_price=Decimal("100"), max_price=Decimal("200"))

    assert no_cache.min_price is None
    assert cached.min_price <= cached.max_price


@pytest.mark.django_db
def test_only_one_primary_media_is_allowed_per_product():
    primary = ProductMediaFactory(is_primary=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductMediaFactory(product=primary.product, is_primary=True)

    ProductMediaFactory(product=primary.product, is_primary=False)
    ProductMediaFactory(is_primary=True)
    assert ProductMedia.objects.count() == 3


@pytest.mark.django_db
def test_attribute_uniqueness_handles_global_and_shop_scopes():
    AttributeFactory(name="Color", code="color", shop=None)
    with pytest.raises(IntegrityError), transaction.atomic():
        AttributeFactory(name="Color", code="another-code", shop=None)

    first_shop = ShopFactory()
    second_shop = ShopFactory()
    AttributeFactory(name="Size", code="size", shop=first_shop)
    AttributeFactory(name="Size", code="size", shop=second_shop)
    with pytest.raises(IntegrityError), transaction.atomic():
        AttributeFactory(name="Other", code="size", shop=first_shop)


@pytest.mark.django_db
def test_attribute_value_and_product_link_are_unique():
    value = AttributeValueFactory(value="Red")
    with pytest.raises(IntegrityError), transaction.atomic():
        AttributeValueFactory(attribute=value.attribute, value="Red")

    product = ProductFactory()
    ProductAttributeValue.objects.create(product=product, attribute_value=value)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductAttributeValue.objects.create(product=product, attribute_value=value)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        {"original_price": Decimal("-1")},
        {"sale_price": Decimal("-1")},
        {"original_price": Decimal("100"), "sale_price": Decimal("101")},
        {"cost_price": Decimal("-1")},
        {"weight_grams": 0},
    ],
)
def test_product_variant_price_and_weight_constraints(overrides):
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductVariantFactory(**overrides)


@pytest.mark.django_db
def test_product_variant_sku_and_non_null_barcode_are_unique_per_shop():
    variant = ProductVariantFactory(sku="SKU-UNIQUE", barcode="893000000001")

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductVariantFactory(
            shop=variant.shop,
            sku="SKU-UNIQUE",
            barcode=None,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductVariantFactory(
            shop=variant.shop,
            sku="OTHER-SKU",
            barcode="893000000001",
        )

    ProductVariantFactory(shop=variant.shop, barcode=None)
    ProductVariantFactory(shop=variant.shop, barcode=None)


@pytest.mark.django_db
def test_original_price_zero_allows_nonnegative_sale_price():
    variant = ProductVariantFactory(
        original_price=Decimal("0"),
        sale_price=Decimal("100"),
    )
    assert variant.sale_price == Decimal("100")


@pytest.mark.django_db
def test_variant_attribute_constraints_allow_one_value_per_attribute():
    variant = ProductVariantFactory()
    attribute = AttributeFactory()
    first_value = AttributeValueFactory(attribute=attribute, value="S")
    second_value = AttributeValueFactory(attribute=attribute, value="M")
    VariantAttributeValue.objects.create(
        variant=variant,
        attribute=attribute,
        attribute_value=first_value,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        VariantAttributeValue.objects.create(
            variant=variant,
            attribute=attribute,
            attribute_value=second_value,
        )


@pytest.mark.django_db
def test_variant_shop_consistency_is_validated_in_service():
    product = ProductFactory()
    ProductVariantService.validate_shop_consistency(product=product, shop=product.shop)

    with pytest.raises(BusinessError, match="không khớp"):
        ProductVariantService.validate_shop_consistency(
            product=product,
            shop=ShopFactory(),
        )


@pytest.mark.django_db
def test_variant_delete_sets_media_variant_to_null():
    media = ProductMediaFactory()
    variant = ProductVariantFactory(product=media.product, shop=media.product.shop)
    media.variant = variant
    media.save(update_fields=("variant", "updated_at"))

    variant.delete()

    media.refresh_from_db()
    assert media.variant_id is None
