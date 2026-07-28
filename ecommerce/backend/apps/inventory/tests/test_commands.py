from io import StringIO

import pytest
from django.core.management import call_command

from apps.inventory.models import InventoryBalance, StockEntry
from apps.product.tests.factories import ProductVariantFactory

pytestmark = pytest.mark.django_db


def test_backfill_inventory_balance_is_idempotent():
    variant = ProductVariantFactory(stock_quantity=13)
    output = StringIO()

    call_command("backfill_inventory_balance", stdout=output)
    call_command("backfill_inventory_balance", stdout=output)

    balance = InventoryBalance.objects.get(variant=variant)
    assert balance.available_stock == 13
    assert InventoryBalance.objects.filter(variant=variant).count() == 1


def test_seed_inventory_demo_creates_one_confirmed_entry_per_shop():
    variant = ProductVariantFactory()
    output = StringIO()

    call_command(
        "seed_inventory_demo",
        quantity=9,
        unit_cost=42000,
        stdout=output,
    )
    call_command(
        "seed_inventory_demo",
        quantity=9,
        unit_cost=42000,
        stdout=output,
    )

    balance = InventoryBalance.objects.get(variant=variant)
    assert balance.available_stock == 9
    assert StockEntry.objects.filter(
        shop=variant.shop,
        note="seed_inventory_demo",
        status=StockEntry.Status.CONFIRMED,
    ).count() == 1
