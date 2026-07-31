from decimal import Decimal

import pytest

from apps.account.models import CustomerProfile
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.cart.models import Cart, CartItem
from apps.cart.services import CartService
from apps.common.exceptions import BusinessError
from apps.inventory.tests.factories import InventoryBalanceFactory
from apps.product.models import Product
from apps.product.tests.factories import ProductVariantFactory


@pytest.fixture
def cart_context(db):
    customer_user = UserFactory(role="customer")
    customer = CustomerProfile.objects.create(user=customer_user)
    shop = ShopFactory()
    variant = ProductVariantFactory(
        shop=shop,
        product__shop=shop,
        product__status=Product.Status.APPROVED,
        sale_price=Decimal("100000"),
    )
    InventoryBalanceFactory(variant=variant, available_stock=5)
    return customer_user, Cart.objects.create(user=customer), variant


@pytest.mark.django_db
def test_add_item_accumulates_and_snapshots_price(cart_context):
    _, cart, variant = cart_context
    first = CartService.add_item(cart, variant, 2)
    second = CartService.add_item(cart, variant, 1)

    assert first.pk == second.pk
    second.refresh_from_db()
    assert second.quantity == 3
    assert second.unit_price_snapshot == Decimal("100000")


@pytest.mark.django_db
def test_add_item_rejects_quantity_above_inventory(cart_context):
    _, cart, variant = cart_context

    with pytest.raises(BusinessError, match="tồn kho"):
        CartService.add_item(cart, variant, 6)


@pytest.mark.django_db
def test_merge_guest_cart_combines_duplicate_variants(cart_context):
    user, cart, variant = cart_context
    CartItem.objects.create(
        cart=cart,
        variant=variant,
        quantity=1,
        unit_price_snapshot=variant.sale_price,
    )

    merged = CartService.merge_guest_cart(
        [
            {"variant_id": variant.id, "quantity": 1},
            {"variant_id": variant.id, "quantity": 2},
        ],
        user,
    )

    assert merged.items.get(variant=variant).quantity == 4
    assert merged.items.filter(variant=variant).count() == 1


@pytest.mark.django_db
def test_cart_summary_marks_price_and_stock_changes(cart_context):
    _, cart, variant = cart_context
    item = CartItem.objects.create(
        cart=cart,
        variant=variant,
        quantity=5,
        unit_price_snapshot=Decimal("90000"),
    )
    variant.inventory_balance.available_stock = 3
    variant.inventory_balance.save(update_fields=("available_stock", "updated_at"))

    summary = CartService.get_cart_summary(cart)
    rendered = summary["shops"][0]["items"][0]

    assert rendered["id"] == str(item.id)
    assert rendered["price_changed"] is True
    assert rendered["is_valid"] is False
    assert rendered["available_stock"] == 3
