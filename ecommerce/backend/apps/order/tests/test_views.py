import pytest
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.order.models import Order
from apps.order.services import CheckoutService
from apps.order.tests.test_services import checkout_fixture

pytestmark = pytest.mark.django_db


def make_order():
    user, customer, address, shop, variant, balance, item = checkout_fixture()
    order, _, _ = CheckoutService.checkout(
        customer=customer,
        cart_item_ids=[item.pk],
        address_id=address.pk,
        coupons={},
        payment_method=Order.PaymentMethod.COD,
        idempotency_key="permission-order",
    )
    return user, shop, order, order.shop_orders.get()


def test_customer_cannot_read_another_customers_order():
    owner, shop, order, shop_order = make_order()
    stranger = UserFactory(role=User.Role.CUSTOMER)
    client = APIClient()
    client.force_authenticate(stranger)

    response = client.get(f"/api/v1/orders/{order.pk}")

    assert response.status_code == 404


def test_seller_queries_are_scoped_to_authenticated_shop():
    owner, shop, order, shop_order = make_order()
    other_shop = ShopFactory()
    client = APIClient()
    client.force_authenticate(other_shop.owner)

    response = client.get(f"/api/v1/seller/orders/{shop_order.pk}")

    assert response.status_code == 404


def test_admin_can_read_any_order():
    owner, shop, order, shop_order = make_order()
    admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
    client = APIClient()
    client.force_authenticate(admin)

    response = client.get(f"/api/v1/admin/orders/{order.pk}")

    assert response.status_code == 200
    assert response.data["data"]["id"] == str(order.pk)
