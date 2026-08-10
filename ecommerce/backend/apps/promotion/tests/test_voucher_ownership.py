from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.account.models import CustomerProfile
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.cart.models import Cart, CartItem
from apps.common.exceptions import BusinessError
from apps.inventory.tests.factories import InventoryBalanceFactory
from apps.product.models import Product
from apps.product.tests.factories import ProductVariantFactory
from apps.promotion.models import UserVoucher, Voucher, VoucherEvent
from apps.promotion.services import UserVoucherService


@pytest.fixture
def ownership_context(db):
    user = UserFactory(role="customer")
    customer = CustomerProfile.objects.create(user=user)
    shop = ShopFactory()
    variant = ProductVariantFactory(
        shop=shop,
        product__shop=shop,
        product__status=Product.Status.APPROVED,
        sale_price=Decimal("100000"),
        original_price=Decimal("120000"),
    )
    InventoryBalanceFactory(variant=variant, available_stock=10)
    cart = Cart.objects.create(user=customer)
    item = CartItem.objects.create(
        cart=cart,
        variant=variant,
        quantity=1,
        unit_price_snapshot=variant.sale_price,
    )
    campaign = Voucher.objects.create(
        scope=Voucher.Scope.PLATFORM,
        code="SAVE20",
        name="Save 20k",
        discount_type=Voucher.DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("20000"),
        min_order_amount=Decimal("50000"),
        total_usage_limit=1,
        remaining_quantity=1,
        usage_limit_per_user=1,
        valid_from=timezone.now() - timezone.timedelta(minutes=1),
        valid_until=timezone.now() + timezone.timedelta(days=1),
    )
    return {
        "user": user,
        "customer": customer,
        "cart": cart,
        "item": item,
        "campaign": campaign,
    }


@pytest.mark.django_db
def test_collect_is_idempotent_and_never_exceeds_quantity(ownership_context):
    campaign = ownership_context["campaign"]
    first, created = UserVoucherService.collect(
        campaign_id=campaign.pk,
        user=ownership_context["user"],
        idempotency_key="same-request",
    )
    repeated, repeated_created = UserVoucherService.collect(
        campaign_id=campaign.pk,
        user=ownership_context["user"],
        idempotency_key="same-request",
    )

    campaign.refresh_from_db()
    assert created is True
    assert repeated_created is False
    assert repeated.pk == first.pk
    assert campaign.remaining_quantity == 0

    other_user = UserFactory(role="customer")
    CustomerProfile.objects.create(user=other_user)
    with pytest.raises(BusinessError, match="hết số lượng"):
        UserVoucherService.collect(
            campaign_id=campaign.pk,
            user=other_user,
            idempotency_key="other-request",
        )


@pytest.mark.django_db
def test_collect_rejects_per_user_limit(ownership_context):
    campaign = ownership_context["campaign"]
    campaign.remaining_quantity = 2
    campaign.total_usage_limit = 2
    campaign.save(update_fields=("remaining_quantity", "total_usage_limit", "updated_at"))
    UserVoucherService.collect(
        campaign_id=campaign.pk,
        user=ownership_context["user"],
        idempotency_key="first",
    )

    with pytest.raises(BusinessError, match="giới hạn"):
        UserVoucherService.collect(
            campaign_id=campaign.pk,
            user=ownership_context["user"],
            idempotency_key="second",
        )


@pytest.mark.django_db
def test_apply_rejects_ineligible_voucher(ownership_context):
    campaign = ownership_context["campaign"]
    campaign.min_order_amount = Decimal("200000")
    campaign.save(update_fields=("min_order_amount", "updated_at"))
    owned, _ = UserVoucherService.collect(
        campaign_id=campaign.pk,
        user=ownership_context["user"],
        idempotency_key="collect",
    )

    with pytest.raises(BusinessError, match="tối thiểu"):
        UserVoucherService.apply(
            cart=ownership_context["cart"],
            user_voucher_ids=[owned.pk],
        )
    owned.refresh_from_db()
    assert owned.status == UserVoucher.Status.SAVED


@pytest.mark.django_db
def test_cancel_rolls_pending_voucher_back_to_saved(ownership_context):
    owned, _ = UserVoucherService.collect(
        campaign_id=ownership_context["campaign"].pk,
        user=ownership_context["user"],
        idempotency_key="collect",
    )
    applied = UserVoucherService.apply(
        cart=ownership_context["cart"],
        user_voucher_ids=[owned.pk],
    )

    assert (
        UserVoucherService.rollback(
            checkout_token=applied["checkout_token"],
            reason="order_cancelled",
        )
        == 1
    )
    owned.refresh_from_db()
    assert owned.status == UserVoucher.Status.SAVED
    assert owned.checkout_token is None
    assert VoucherEvent.objects.filter(
        user_voucher=owned,
        action=VoucherEvent.Action.ROLLBACK,
    ).exists()


@pytest.mark.django_db
def test_expire_vouchers_command_marks_saved_ownership_expired(ownership_context):
    owned, _ = UserVoucherService.collect(
        campaign_id=ownership_context["campaign"].pk,
        user=ownership_context["user"],
        idempotency_key="collect",
    )
    campaign = ownership_context["campaign"]
    campaign.valid_until = timezone.now() - timezone.timedelta(seconds=1)
    campaign.save(update_fields=("valid_until", "updated_at"))

    call_command("expire_vouchers")

    owned.refresh_from_db()
    assert owned.status == UserVoucher.Status.EXPIRED


@pytest.mark.django_db
def test_voucher_center_collect_wallet_and_checkout_api(ownership_context):
    client = APIClient()
    client.force_authenticate(ownership_context["user"])
    campaign = ownership_context["campaign"]

    center = client.get("/api/v1/voucher-center")
    assert center.status_code == 200
    assert center.data["data"][0]["id"] == str(campaign.pk)

    collected = client.post(
        f"/api/v1/vouchers/{campaign.pk}/collect",
        {"idempotency_key": "api-collect"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="api-collect",
    )
    assert collected.status_code == 201
    user_voucher_id = collected.data["data"]["id"]

    wallet = client.get("/api/v1/me/vouchers", {"status": "saved"})
    assert wallet.status_code == 200
    assert wallet.data["data"][0]["id"] == user_voucher_id

    available = client.get("/api/v1/checkout/available-vouchers")
    assert available.status_code == 200
    assert available.data["data"]["best_voucher_id"] == user_voucher_id

    applied = client.post(
        "/api/v1/checkout/apply-voucher",
        {
            "user_voucher_ids": [user_voucher_id],
            "selected_item_ids": [str(ownership_context["item"].pk)],
        },
        format="json",
    )
    assert applied.status_code == 200
    assert applied.data["data"]["discount"] == Decimal("20000")
    assert applied.data["data"]["checkout_token"]


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="Collect row-lock concurrency contract requires PostgreSQL",
)
class VoucherCollectConcurrencyTests(TransactionTestCase):
    def setUp(self):
        now = timezone.now()
        self.campaign = Voucher.objects.create(
            scope=Voucher.Scope.PLATFORM,
            code="ONLY3",
            name="Only three",
            discount_type=Voucher.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("1000"),
            total_usage_limit=3,
            remaining_quantity=3,
            usage_limit_per_user=1,
            valid_from=now - timezone.timedelta(minutes=1),
            valid_until=now + timezone.timedelta(hours=1),
        )
        self.users = []
        for index in range(8):
            user = UserFactory(role="customer", email=f"collector-{index}@example.com")
            CustomerProfile.objects.create(user=user)
            self.users.append(user)

    def _collect(self, user) -> bool:
        close_old_connections()
        try:
            UserVoucherService.collect(
                campaign_id=self.campaign.pk,
                user=user,
                idempotency_key=f"collect:{user.pk}",
            )
            return True
        except BusinessError:
            return False
        finally:
            close_old_connections()

    def test_concurrent_collect_never_oversells(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(self._collect, self.users))
        self.campaign.refresh_from_db()
        self.assertEqual(sum(results), 3)
        self.assertEqual(self.campaign.remaining_quantity, 0)
        self.assertEqual(UserVoucher.objects.filter(voucher_campaign=self.campaign).count(), 3)
