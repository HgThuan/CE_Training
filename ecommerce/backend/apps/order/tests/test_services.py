from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import close_old_connections, connection

from apps.account.models import Address, CustomerProfile, User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.cart.models import Cart, CartItem
from apps.inventory.models import InventoryBalance, StockReservation
from apps.order.models import Order, OrderCancellation, ShopOrder
from apps.order.services import CheckoutService, OrderService
from apps.order.state_machine import OrderStateMachine
from apps.payment.models import Payment, Refund
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory, ProductVariantFactory

pytestmark = pytest.mark.django_db


def checkout_fixture():
    user = UserFactory(role=User.Role.CUSTOMER)
    customer = CustomerProfile.objects.get_or_create(user=user)[0]
    address = Address.objects.create(
        user=user,
        recipient_name="Nguyen Van A",
        phone="0901234567",
        province="HCM",
        district="Quan 1",
        ward="Ben Nghe",
        detail_address="1 Le Loi",
        is_default=True,
    )
    shop = ShopFactory()
    product = ProductFactory(shop=shop, status=Product.Status.APPROVED)
    variant = ProductVariantFactory(
        product=product,
        shop=shop,
        original_price=Decimal("100000"),
        sale_price=Decimal("90000"),
    )
    balance = InventoryBalance.objects.create(variant=variant, available_stock=5)
    cart = Cart.objects.create(user=customer)
    item = CartItem.objects.create(
        cart=cart,
        variant=variant,
        quantity=2,
        unit_price_snapshot=variant.sale_price,
    )
    return user, customer, address, shop, variant, balance, item


def test_checkout_is_idempotent_and_reserves_stock():
    user, customer, address, shop, variant, balance, item = checkout_fixture()
    kwargs = {
        "customer": customer,
        "cart_item_ids": [item.pk],
        "address_id": address.pk,
        "coupons": {},
        "payment_method": Order.PaymentMethod.COD,
        "idempotency_key": "checkout-once",
        "shop_notes": {str(shop.pk): "Gọi trước khi giao"},
        "shipping_methods": {str(shop.pk): {"code": "STANDARD"}},
    }
    order, payment_url, created = CheckoutService.checkout(**kwargs)
    retry, retry_url, retry_created = CheckoutService.checkout(**kwargs)

    assert created is True
    assert retry_created is False
    assert retry.pk == order.pk
    assert payment_url is retry_url is None
    assert Order.objects.count() == 1
    assert order.shop_orders.count() == 1
    shop_order = order.shop_orders.get()
    assert shop_order.seller_note == "Gọi trước khi giao"
    assert shop_order.shipping_method_code == "STANDARD"
    balance.refresh_from_db()
    assert (balance.available_stock, balance.reserved_stock) == (3, 2)
    assert StockReservation.objects.get().status == StockReservation.Status.ACTIVE


def test_confirm_commits_and_seller_cancel_adjusts_committed_stock():
    user, customer, address, shop, variant, balance, item = checkout_fixture()
    order, _, _ = CheckoutService.checkout(
        customer=customer,
        cart_item_ids=[item.pk],
        address_id=address.pk,
        coupons={},
        payment_method=Order.PaymentMethod.COD,
        idempotency_key="commit-cancel",
    )
    shop_order = order.shop_orders.get()
    OrderService.confirm(shop_order, shop.owner)
    balance.refresh_from_db()
    assert (balance.available_stock, balance.reserved_stock) == (3, 0)

    OrderService.cancel(shop_order, shop.owner, "OUT_OF_STOCK", "Kiểm kê lệch")
    balance.refresh_from_db()
    shop_order.refresh_from_db()
    assert balance.available_stock == 5
    assert shop_order.fulfillment_status == ShopOrder.FulfillmentStatus.CANCELLED
    assert OrderCancellation.objects.get(shop_order=shop_order).stock_restored_at is not None


def test_state_machine_rejects_skips_and_scopes_customer_cancel():
    status = ShopOrder.FulfillmentStatus
    assert OrderStateMachine.can_transition(
        status.PENDING_CONFIRMATION, status.CONFIRMED, User.Role.SELLER
    )
    assert not OrderStateMachine.can_transition(
        status.PENDING_CONFIRMATION, status.SHIPPING, User.Role.SELLER
    )
    assert OrderStateMachine.can_transition(
        status.PENDING_CONFIRMATION, status.CANCELLED, User.Role.CUSTOMER
    )
    assert not OrderStateMachine.can_transition(
        status.CONFIRMED, status.CANCELLED, User.Role.CUSTOMER
    )


def test_cod_delivery_records_collection_without_changing_order_payment_status():
    user, customer, address, shop, variant, balance, item = checkout_fixture()
    order, _, _ = CheckoutService.checkout(
        customer=customer,
        cart_item_ids=[item.pk],
        address_id=address.pk,
        coupons={},
        payment_method=Order.PaymentMethod.COD,
        idempotency_key="cod-delivery",
    )
    shop_order = OrderService.confirm(order.shop_orders.get(), shop.owner)
    shop_order = OrderService.transition_status(
        shop_order, ShopOrder.FulfillmentStatus.PACKING, shop.owner
    )
    shop_order = OrderService.transition_status(
        shop_order, ShopOrder.FulfillmentStatus.SHIPPING, shop.owner
    )
    shop_order = OrderService.transition_status(
        shop_order, ShopOrder.FulfillmentStatus.DELIVERED, shop.owner
    )
    order.refresh_from_db()
    assert shop_order.cod_collected_at is not None
    assert order.payment_status == Order.PaymentStatus.PENDING


def test_paid_seller_cancellation_creates_shop_level_refund():
    user, customer, address, shop, variant, balance, item = checkout_fixture()
    order, _, _ = CheckoutService.checkout(
        customer=customer,
        cart_item_ids=[item.pk],
        address_id=address.pk,
        coupons={},
        payment_method=Order.PaymentMethod.COD,
        idempotency_key="paid-refund",
    )
    order.payment_method = Order.PaymentMethod.VNPAY
    order.payment_status = Order.PaymentStatus.PAID
    order.save(update_fields=("payment_method", "payment_status", "updated_at"))
    Payment.objects.create(
        order=order,
        payment_code="PAY-REFUND",
        method=Order.PaymentMethod.VNPAY,
        provider="VNPAY",
        amount=order.grand_total,
        status=Payment.Status.PAID,
        idempotency_key="refund-payment",
    )
    shop_order = OrderService.confirm(order.shop_orders.get(), shop.owner)

    OrderService.cancel(shop_order, shop.owner, "SELLER_CANCEL")

    refund = Refund.objects.get(shop_order=shop_order)
    assert refund.payment.order_id == order.pk
    assert refund.amount == shop_order.total_amount
    assert refund.status == Refund.Status.PENDING


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkout_cannot_oversell():
    if connection.vendor != "postgresql":
        pytest.skip("SELECT FOR UPDATE concurrency contract requires PostgreSQL")
    first_user, first_customer, first_address, shop, variant, balance, first_item = (
        checkout_fixture()
    )
    balance.available_stock = 1
    balance.save(update_fields=("available_stock", "updated_at"))
    second_user = UserFactory(role=User.Role.CUSTOMER)
    second_customer = CustomerProfile.objects.get_or_create(user=second_user)[0]
    second_address = Address.objects.create(
        user=second_user,
        recipient_name="Customer 2",
        phone="0901234568",
        province="HCM",
        district="Quan 1",
        ward="Ben Nghe",
        detail_address="2 Le Loi",
    )
    second_cart = Cart.objects.create(user=second_customer)
    second_item = CartItem.objects.create(
        cart=second_cart,
        variant=variant,
        quantity=1,
        unit_price_snapshot=variant.sale_price,
    )
    first_item.quantity = 1
    first_item.save(update_fields=("quantity", "updated_at"))

    def worker(customer_id, address_id, item_id, key):
        close_old_connections()
        try:
            customer = CustomerProfile.objects.get(pk=customer_id)
            CheckoutService.checkout(
                customer=customer,
                cart_item_ids=[item_id],
                address_id=address_id,
                coupons={},
                payment_method=Order.PaymentMethod.COD,
                idempotency_key=key,
            )
            return "created"
        except Exception:
            return "rejected"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda args: worker(*args),
                [
                    (first_customer.pk, first_address.pk, first_item.pk, "race-1"),
                    (second_customer.pk, second_address.pk, second_item.pk, "race-2"),
                ],
            )
        )

    assert sorted(outcomes) == ["created", "rejected"]
    balance.refresh_from_db()
    assert balance.available_stock == 0
