import factory

from apps.account.tests.factories import ShopFactory, UserFactory
from apps.inventory.models import (
    InventoryBalance,
    StockAlert,
    StockEntry,
    StockEntryItem,
    StockOutEntry,
    StockOutEntryItem,
)
from apps.product.tests.factories import ProductVariantFactory


class InventoryBalanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InventoryBalance

    variant = factory.SubFactory(ProductVariantFactory)
    available_stock = 10
    reserved_stock = 0
    low_stock_threshold = 5


class StockEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StockEntry

    shop = factory.SubFactory(ShopFactory)
    supplier_name = "Nhà cung cấp Demo"
    created_by = factory.LazyAttribute(lambda entry: entry.shop.owner)


class StockEntryItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StockEntryItem

    stock_entry = factory.SubFactory(StockEntryFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = 5
    unit_cost = 50000


class StockOutEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StockOutEntry

    shop = factory.SubFactory(ShopFactory)
    entry_type = StockOutEntry.EntryType.OUT
    reason = "Hàng hỏng"
    created_by = factory.LazyAttribute(lambda entry: entry.shop.owner)


class StockOutEntryItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StockOutEntryItem

    stock_out_entry = factory.SubFactory(StockOutEntryFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = 2


class StockAlertFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StockAlert

    variant = factory.SubFactory(ProductVariantFactory)
    user = factory.SubFactory(UserFactory)
