from decimal import Decimal

import factory

from apps.account.tests.factories import ShopFactory
from apps.catalog.tests.factories import CategoryFactory
from apps.product.models import (
    Attribute,
    AttributeValue,
    Product,
    ProductMedia,
    ProductVariant,
)


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    shop = factory.SubFactory(ShopFactory)
    category = factory.SubFactory(CategoryFactory)
    name = factory.Sequence(lambda number: f"Product {number}")
    slug = factory.Sequence(lambda number: f"product-{number}")


class AttributeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Attribute

    name = factory.Sequence(lambda number: f"Attribute {number}")
    code = factory.Sequence(lambda number: f"attribute_{number}")


class AttributeValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttributeValue

    attribute = factory.SubFactory(AttributeFactory)
    value = factory.Sequence(lambda number: f"Value {number}")


class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    shop = factory.LazyAttribute(lambda variant: variant.product.shop)
    sku = factory.Sequence(lambda number: f"SKU-{number}")
    original_price = Decimal("100000")
    sale_price = Decimal("90000")


class ProductMediaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductMedia

    product = factory.SubFactory(ProductFactory)
    file_url = factory.Sequence(lambda number: f"https://cdn.example.com/product-{number}.webp")
