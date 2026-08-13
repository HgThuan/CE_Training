from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.account.models import CustomerProfile
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.cart.models import Cart, CartItem
from apps.common.exceptions import BusinessError
from apps.inventory.tests.factories import InventoryBalanceFactory
from apps.product.models import Product
from apps.product.tests.factories import ProductVariantFactory
from apps.promotion.models import FlashSale, FlashSaleItem, Voucher, VoucherUsage
from apps.promotion.services import (
    FlashSaleService,
    PromotionCalculationService,
    VoucherService,
)


@pytest.fixture
def promotion_context(db):
    user = UserFactory(role="customer")
    customer = CustomerProfile.objects.create(user=user)
    shop = ShopFactory()
    variant = ProductVariantFactory(
        shop=shop,
        product__shop=shop,
        product__status=Product.Status.APPROVED,
        sale_price=Decimal("200000"),
        original_price=Decimal("250000"),
    )
    InventoryBalanceFactory(variant=variant, available_stock=20)
    cart = Cart.objects.create(user=customer)
    item = CartItem.objects.create(
        cart=cart,
        variant=variant,
        quantity=1,
        unit_price_snapshot=variant.sale_price,
    )
    now = timezone.now()
    platform = Voucher.objects.create(
        scope=Voucher.Scope.PLATFORM,
        code="PLATFORM50",
        name="Platform",
        discount_type=Voucher.DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("50000"),
        min_order_amount=Decimal("100000"),
        total_usage_limit=10,
        valid_from=now - timezone.timedelta(hours=1),
        valid_until=now + timezone.timedelta(hours=1),
    )
    shop_voucher = Voucher.objects.create(
        scope=Voucher.Scope.SHOP,
        shop=shop,
        code="SHOP10",
        name="Shop",
        discount_type=Voucher.DiscountType.PERCENTAGE,
        discount_value=Decimal("10"),
        max_discount_amount=Decimal("30000"),
        min_order_amount=Decimal("100000"),
        total_usage_limit=10,
        valid_from=now - timezone.timedelta(hours=1),
        valid_until=now + timezone.timedelta(hours=1),
    )
    return {
        "user": user,
        "customer": customer,
        "shop": shop,
        "variant": variant,
        "cart": cart,
        "item": item,
        "platform": platform,
        "shop_voucher": shop_voucher,
        "now": now,
    }


@pytest.mark.django_db
def test_voucher_rejects_expired(promotion_context):
    voucher = promotion_context["platform"]
    voucher.valid_until = timezone.now() - timezone.timedelta(seconds=1)
    voucher.save(update_fields=("valid_until", "updated_at"))
    with pytest.raises(BusinessError, match="hết hạn"):
        VoucherService.validate_and_apply(
            voucher.code,
            promotion_context["customer"],
            Decimal("200000"),
        )


@pytest.mark.django_db
def test_voucher_rejects_below_minimum(promotion_context):
    with pytest.raises(BusinessError, match="tối thiểu"):
        VoucherService.validate_and_apply(
            promotion_context["platform"].code,
            promotion_context["customer"],
            Decimal("50000"),
        )


@pytest.mark.django_db
def test_voucher_rejects_wrong_shop_scope(promotion_context):
    other_shop = ShopFactory()
    with pytest.raises(BusinessError, match="shop"):
        VoucherService.validate_and_apply(
            promotion_context["shop_voucher"].code,
            promotion_context["customer"],
            Decimal("200000"),
            shop=other_shop,
        )


@pytest.mark.django_db
def test_voucher_rejects_total_and_per_user_limits(promotion_context):
    voucher = promotion_context["platform"]
    voucher.total_usage_limit = 1
    voucher.save(update_fields=("total_usage_limit", "updated_at"))
    VoucherUsage.objects.create(
        voucher=voucher,
        user=promotion_context["customer"],
        order_reference="ORDER-1",
        discount_amount=Decimal("50000"),
    )
    with pytest.raises(BusinessError, match="hết lượt"):
        VoucherService.validate_and_apply(
            voucher.code,
            promotion_context["customer"],
            Decimal("200000"),
        )


@pytest.mark.django_db
def test_promotion_stacks_shop_then_platform(promotion_context):
    result = PromotionCalculationService.calculate(
        promotion_context["cart"],
        [promotion_context["item"].id],
        {
            "platform": [promotion_context["platform"].code],
            "shops": {
                str(promotion_context["shop"].id): [
                    promotion_context["shop_voucher"].code
                ]
            },
        },
    )

    assert result["subtotal"] == Decimal("200000")
    assert result["discount"] == Decimal("70000")
    assert result["total"] == Decimal("130000")
    assert [entry["scope"] for entry in result["shops"][0]["discounts"]] == [
        Voucher.Scope.SHOP,
        Voucher.Scope.PLATFORM,
    ]


@pytest.mark.django_db
def test_promotion_rejects_two_vouchers_of_same_scope(promotion_context):
    with pytest.raises(BusinessError, match="tối đa 1 voucher sàn"):
        PromotionCalculationService.calculate(
            promotion_context["cart"],
            voucher_codes={"platform": ["A", "B"]},
        )


@pytest.mark.django_db
def test_flash_sale_price_is_base_before_vouchers(promotion_context):
    sale = FlashSale.objects.create(
        name="Noon",
        start_time=promotion_context["now"] - timezone.timedelta(minutes=5),
        end_time=promotion_context["now"] + timezone.timedelta(minutes=5),
    )
    FlashSaleItem.objects.create(
        flash_sale=sale,
        variant=promotion_context["variant"],
        sale_price=Decimal("150000"),
        quota=3,
    )

    result = PromotionCalculationService.calculate(
        promotion_context["cart"],
        voucher_codes={
            "shops": {
                str(promotion_context["shop"].id): promotion_context["shop_voucher"].code
            }
        },
    )

    assert result["subtotal"] == Decimal("150000")
    assert result["discount"] == Decimal("15000")
    assert result["total"] == Decimal("135000")


@pytest.mark.django_db
def test_flash_sale_reservation_rejects_oversell(promotion_context):
    sale = FlashSale.objects.create(
        name="Noon",
        start_time=promotion_context["now"] - timezone.timedelta(minutes=5),
        end_time=promotion_context["now"] + timezone.timedelta(minutes=5),
    )
    item = FlashSaleItem.objects.create(
        flash_sale=sale,
        variant=promotion_context["variant"],
        sale_price=Decimal("150000"),
        quota=2,
    )
    FlashSaleService.reserve_flash_sale_quota(item, 2)
    with pytest.raises(BusinessError, match="hết số lượng"):
        FlashSaleService.reserve_flash_sale_quota(item, 1)


@pytest.mark.django_db
def test_successful_purchase_consumes_flash_quota_by_variant(promotion_context):
    variant = promotion_context["variant"]
    sale = FlashSale.objects.create(
        name="Any entry point",
        start_time=timezone.now() - timezone.timedelta(minutes=1),
        end_time=timezone.now() + timezone.timedelta(hours=1),
    )
    item = FlashSaleItem.objects.create(
        flash_sale=sale,
        variant=variant,
        sale_price=Decimal("150000"),
        quota=3,
    )

    consumed = FlashSaleService.commit_successful_purchase(
        [{"variant_id": variant.pk, "quantity": 2}]
    )

    item.refresh_from_db()
    assert [entry.pk for entry in consumed] == [item.pk]
    assert item.sold_count == 2
    with pytest.raises(BusinessError, match="chỉ còn 1"):
        FlashSaleService.commit_successful_purchase(
            [{"variant_id": variant.pk, "quantity": 2}]
        )
    item.refresh_from_db()
    assert item.sold_count == 2


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="Row-lock concurrency contract requires PostgreSQL",
)
class PromotionConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = UserFactory(role="customer")
        self.customer = CustomerProfile.objects.create(user=self.user)
        self.shop = ShopFactory()
        self.variant = ProductVariantFactory(
            shop=self.shop,
            product__shop=self.shop,
            product__status=Product.Status.APPROVED,
        )
        now = timezone.now()
        self.voucher = Voucher.objects.create(
            scope=Voucher.Scope.PLATFORM,
            code="LIMIT3",
            name="Limited",
            discount_type=Voucher.DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("1000"),
            total_usage_limit=3,
            usage_limit_per_user=10,
            valid_from=now - timezone.timedelta(minutes=1),
            valid_until=now + timezone.timedelta(minutes=10),
        )
        self.sale = FlashSale.objects.create(
            name="Concurrent",
            start_time=now - timezone.timedelta(minutes=1),
            end_time=now + timezone.timedelta(minutes=10),
        )
        self.flash_item = FlashSaleItem.objects.create(
            flash_sale=self.sale,
            variant=self.variant,
            sale_price=Decimal("50000"),
            quota=3,
        )

    def _use_voucher(self, number):
        close_old_connections()
        try:
            VoucherService.validate_and_apply(
                self.voucher.code,
                self.customer,
                Decimal("100000"),
                commit=True,
                order_reference=f"ORDER-{number}",
            )
            return True
        except BusinessError:
            return False
        finally:
            close_old_connections()

    def _reserve_flash(self):
        close_old_connections()
        try:
            FlashSaleService.reserve_flash_sale_quota(self.flash_item.pk, 1)
            return True
        except BusinessError:
            return False
        finally:
            close_old_connections()

    def test_concurrent_voucher_usage_never_exceeds_limit(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(self._use_voucher, range(8)))
        self.assertEqual(sum(results), 3)
        self.assertEqual(VoucherUsage.objects.filter(voucher=self.voucher).count(), 3)

    def test_concurrent_flash_sale_never_oversells(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: self._reserve_flash(), range(8)))
        self.flash_item.refresh_from_db()
        self.assertEqual(sum(results), 3)
        self.assertEqual(self.flash_item.sold_count, 3)
