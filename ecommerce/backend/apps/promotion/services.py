from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.common.exceptions import BusinessError
from apps.promotion.models import FlashSaleItem, Voucher, VoucherUsage

VND_QUANTUM = Decimal("1")
MAX_PLATFORM_VOUCHERS_PER_SHOP_ORDER = 1
MAX_SHOP_VOUCHERS_PER_SHOP_ORDER = 1


def round_vnd(value: Decimal) -> Decimal:
    return Decimal(value).quantize(VND_QUANTUM, rounding=ROUND_HALF_UP)


class VoucherService:
    @staticmethod
    def _discount(voucher: Voucher, amount: Decimal) -> Decimal:
        if voucher.discount_type == Voucher.DiscountType.PERCENTAGE:
            discount = amount * voucher.discount_value / Decimal("100")
            if voucher.max_discount_amount is not None:
                discount = min(discount, voucher.max_discount_amount)
        else:
            discount = voucher.discount_value
        return min(amount, round_vnd(discount))

    @classmethod
    def validate_and_apply(
        cls,
        voucher_code: str,
        user,
        shop_order_amount: Decimal,
        shop=None,
        *,
        commit: bool = False,
        order_reference: str | None = None,
    ) -> Decimal:
        """Validate and calculate a voucher discount.

        The default ``commit=False`` is a side-effect-free preview. ``commit=True``
        locks the voucher row and creates one ``VoucherUsage`` record atomically;
        Sprint 07 checkout must provide a stable ``order_reference``.
        """
        if commit and (user is None or not order_reference):
            raise BusinessError("Cần customer và order_reference khi ghi nhận voucher")

        def execute() -> Decimal:
            queryset = Voucher.objects.select_related("shop")
            if commit:
                queryset = queryset.select_for_update()
            try:
                voucher = queryset.get(code__iexact=voucher_code.strip())
            except Voucher.DoesNotExist as exc:
                raise BusinessError("Voucher không tồn tại") from exc

            now = timezone.now()
            if not voucher.is_active or not voucher.valid_from <= now <= voucher.valid_until:
                raise BusinessError("Voucher chưa có hiệu lực hoặc đã hết hạn")
            amount = round_vnd(Decimal(shop_order_amount))
            if amount < voucher.min_order_amount:
                raise BusinessError("Đơn hàng chưa đạt giá trị tối thiểu")
            if voucher.scope == Voucher.Scope.SHOP:
                if shop is None or voucher.shop_id != shop.id:
                    raise BusinessError("Voucher không áp dụng cho shop này")
            elif voucher.shop_id is not None:
                raise BusinessError("Cấu hình voucher sàn không hợp lệ")

            total_used = VoucherUsage.objects.filter(voucher=voucher).count()
            if voucher.total_usage_limit is not None and total_used >= voucher.total_usage_limit:
                raise BusinessError("Voucher đã hết lượt sử dụng")
            if user is not None:
                user_used = VoucherUsage.objects.filter(voucher=voucher, user=user).count()
                if user_used >= voucher.usage_limit_per_user:
                    raise BusinessError("Bạn đã hết lượt sử dụng voucher này")

            discount = cls._discount(voucher, amount)
            if commit:
                try:
                    VoucherUsage.objects.create(
                        voucher=voucher,
                        user=user,
                        order_reference=order_reference,
                        discount_amount=discount,
                    )
                except IntegrityError as exc:
                    raise BusinessError("Voucher đã được ghi nhận cho lượt checkout này") from exc
            return discount

        if commit:
            with transaction.atomic():
                return execute()
        return execute()


class FlashSaleService:
    @staticmethod
    def get_active_item(variant) -> FlashSaleItem | None:
        now = timezone.now()
        return (
            FlashSaleItem.objects.select_related("flash_sale")
            .filter(
                variant=variant,
                flash_sale__is_active=True,
                flash_sale__start_time__lte=now,
                flash_sale__end_time__gte=now,
                sold_count__lt=F("quota"),
            )
            .order_by("sale_price", "flash_sale__end_time")
            .first()
        )

    @classmethod
    def get_active_price(cls, variant) -> Decimal:
        """Return current Flash Sale price or the variant's ordinary sale price."""
        item = cls.get_active_item(variant)
        return item.sale_price if item else variant.sale_price

    @staticmethod
    def reserve_flash_sale_quota(flash_sale_item, quantity: int) -> FlashSaleItem:
        """Atomically reserve Flash Sale quota for Sprint 07 checkout."""
        if quantity <= 0:
            raise BusinessError("Số lượng Flash Sale phải lớn hơn 0")
        item_id = getattr(flash_sale_item, "pk", flash_sale_item)
        with transaction.atomic():
            item = (
                FlashSaleItem.objects.select_for_update()
                .select_related("flash_sale")
                .get(pk=item_id)
            )
            now = timezone.now()
            if (
                not item.flash_sale.is_active
                or not item.flash_sale.start_time <= now <= item.flash_sale.end_time
            ):
                raise BusinessError("Flash Sale không còn hiệu lực")
            if item.sold_count + quantity > item.quota:
                raise BusinessError("Flash Sale đã hết số lượng")
            item.sold_count = F("sold_count") + quantity
            item.save(update_fields=("sold_count", "updated_at"))
            item.refresh_from_db()
            return item


class PromotionCalculationService:
    """Side-effect-free cart pricing shared by preview and Sprint 07 checkout."""

    @staticmethod
    def _voucher_map(codes: list[str]) -> dict[str, Voucher]:
        normalized = [code.strip().upper() for code in codes if code and code.strip()]
        vouchers = Voucher.objects.select_related("shop", "applicable_category").filter(
            code__in=normalized
        )
        return {voucher.code: voucher for voucher in vouchers}

    @classmethod
    def calculate(
        cls,
        cart,
        selected_item_ids: list | None = None,
        voucher_codes: dict | None = None,
    ) -> dict:
        """Calculate Flash Sale prices then stack one platform + one shop voucher.

        Flash Sale is deliberately treated as the item's base price. Vouchers
        are applied after that price is selected. This method never reserves
        stock/quota and never creates ``VoucherUsage``.
        """
        voucher_codes = voucher_codes or {}
        platform_codes = voucher_codes.get("platform", [])
        if isinstance(platform_codes, str):
            platform_codes = [platform_codes]
        shop_codes = voucher_codes.get("shops", {})
        if len(platform_codes) > MAX_PLATFORM_VOUCHERS_PER_SHOP_ORDER:
            raise BusinessError("Chỉ được dùng tối đa 1 voucher sàn")
        for raw_codes in shop_codes.values():
            codes = [raw_codes] if isinstance(raw_codes, str) else raw_codes
            if len(codes) > MAX_SHOP_VOUCHERS_PER_SHOP_ORDER:
                raise BusinessError("Mỗi shop chỉ được dùng tối đa 1 voucher shop")

        selected_ids = {str(value) for value in selected_item_ids or []}
        items = cart.items.select_related(
            "variant__inventory_balance",
            "variant__product__shop",
            "variant__product__category",
        )
        if selected_ids:
            items = items.filter(id__in=selected_ids)
        else:
            items = items.filter(is_selected=True)

        all_codes = list(platform_codes)
        for raw_codes in shop_codes.values():
            all_codes.extend([raw_codes] if isinstance(raw_codes, str) else raw_codes)
        vouchers = cls._voucher_map(all_codes)
        missing = {code.strip().upper() for code in all_codes} - vouchers.keys()
        if missing:
            raise BusinessError(f"Voucher không tồn tại: {', '.join(sorted(missing))}")

        shops: OrderedDict[int, dict[str, Any]] = OrderedDict()
        for item in items:
            variant = item.variant
            product = variant.product
            shop = variant.shop
            if item.quantity > variant.available_stock:
                raise BusinessError(
                    "Giỏ hàng có sản phẩm không đủ tồn kho",
                    errors={"item_id": [str(item.id)]},
                )
            flash_item = FlashSaleService.get_active_item(variant)
            unit_price = flash_item.sale_price if flash_item else variant.sale_price
            line_total = unit_price * item.quantity
            shop_data = shops.setdefault(
                shop.id,
                {
                    "shop_id": shop.id,
                    "shop_name": shop.name,
                    "items": [],
                    "subtotal": Decimal("0"),
                    "discounts": [],
                    "total": Decimal("0"),
                },
            )
            shop_data["items"].append(
                {
                    "item_id": str(item.id),
                    "variant_id": str(variant.id),
                    "quantity": item.quantity,
                    "unit_price": unit_price,
                    "is_flash_sale": flash_item is not None,
                    "line_total": line_total,
                    "category_id": str(product.category_id),
                }
            )
            shop_data["subtotal"] += line_total

        customer = cart.user
        grand_subtotal = Decimal("0")
        grand_discount = Decimal("0")
        platform_code = platform_codes[0].strip().upper() if platform_codes else None

        for shop_id, shop_data in shops.items():
            subtotal = shop_data["subtotal"]
            running_total = subtotal
            raw_shop_codes = shop_codes.get(str(shop_id), shop_codes.get(shop_id, []))
            normalized_shop_codes = (
                [raw_shop_codes] if isinstance(raw_shop_codes, str) else raw_shop_codes
            )
            if normalized_shop_codes:
                code = normalized_shop_codes[0].strip().upper()
                voucher = vouchers[code]
                if voucher.scope != Voucher.Scope.SHOP:
                    raise BusinessError(f"{code} không phải voucher shop")
                discount = VoucherService.validate_and_apply(
                    code,
                    customer,
                    running_total,
                    shop=voucher.shop,
                )
                if voucher.shop_id != shop_id:
                    raise BusinessError(f"{code} không áp dụng cho shop này")
                shop_data["discounts"].append(
                    {"scope": Voucher.Scope.SHOP, "code": code, "amount": discount}
                )
                running_total -= discount

            if platform_code:
                voucher = vouchers[platform_code]
                if voucher.scope != Voucher.Scope.PLATFORM:
                    raise BusinessError(f"{platform_code} không phải voucher sàn")
                eligible_amount = running_total
                if voucher.applicable_category_id:
                    eligible_subtotal = sum(
                        line["line_total"]
                        for line in shop_data["items"]
                        if line["category_id"] == str(voucher.applicable_category_id)
                    )
                    eligible_amount = min(running_total, eligible_subtotal)
                discount = VoucherService.validate_and_apply(
                    platform_code,
                    customer,
                    eligible_amount,
                )
                shop_data["discounts"].append(
                    {"scope": Voucher.Scope.PLATFORM, "code": platform_code, "amount": discount}
                )
                running_total -= discount

            shop_data["total"] = max(Decimal("0"), running_total)
            grand_subtotal += subtotal
            grand_discount += subtotal - shop_data["total"]

        return {
            "shops": list(shops.values()),
            "subtotal": grand_subtotal,
            "discount": grand_discount,
            "total": max(Decimal("0"), grand_subtotal - grand_discount),
        }
