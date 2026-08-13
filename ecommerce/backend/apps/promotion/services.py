from collections import OrderedDict
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID, uuid4

from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.account.models import CustomerProfile
from apps.common.exceptions import BusinessError
from apps.promotion.models import (
    FlashSale,
    FlashSaleItem,
    UserVoucher,
    Voucher,
    VoucherEvent,
    VoucherUsage,
)

VND_QUANTUM = Decimal("1")
MAX_PLATFORM_VOUCHERS_PER_SHOP_ORDER = 1
MAX_SHOP_VOUCHERS_PER_SHOP_ORDER = 1


def round_vnd(value: Decimal) -> Decimal:
    return Decimal(value).quantize(VND_QUANTUM, rounding=ROUND_HALF_UP)


class VoucherService:
    @staticmethod
    def _discount(voucher: Voucher, amount: Decimal) -> Decimal:
        if voucher.discount_type == Voucher.DiscountType.FREESHIP:
            raise BusinessError("Voucher freeship cần phí vận chuyển từ bước checkout")
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


class UserVoucherService:
    PENDING_TTL = timedelta(minutes=15)

    @staticmethod
    def customer_for(user) -> CustomerProfile:
        if isinstance(user, CustomerProfile):
            return user
        customer, _ = CustomerProfile.objects.get_or_create(user=user)
        return customer

    @classmethod
    def release_expired_pending(cls, *, customer: CustomerProfile | None = None) -> int:
        queryset = UserVoucher.objects.filter(
            status=UserVoucher.Status.PENDING_USE,
            pending_expires_at__lte=timezone.now(),
        )
        if customer is not None:
            queryset = queryset.filter(user=customer)
        expired = list(queryset.select_related("voucher_campaign"))
        if not expired:
            return 0
        ids = [item.pk for item in expired]
        updated = UserVoucher.objects.filter(pk__in=ids).update(
            status=UserVoucher.Status.SAVED,
            checkout_token=None,
            pending_expires_at=None,
            updated_at=timezone.now(),
        )
        VoucherEvent.objects.bulk_create(
            [
                VoucherEvent(
                    user_voucher=item,
                    action=VoucherEvent.Action.ROLLBACK,
                    metadata={"reason": "pending_ttl_expired"},
                )
                for item in expired
            ]
        )
        return updated

    @classmethod
    def collect(
        cls,
        *,
        campaign_id,
        user,
        idempotency_key: str,
    ) -> tuple[UserVoucher, bool]:
        customer = cls.customer_for(user)
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise BusinessError(
                "Thiếu Idempotency-Key cho thao tác lưu voucher",
                errors={"idempotency_key": ["Trường này là bắt buộc"]},
            )
        with transaction.atomic():
            campaign = Voucher.objects.select_for_update().get(pk=campaign_id)
            existing = UserVoucher.objects.filter(
                user=customer,
                idempotency_key=normalized_key,
            ).first()
            if existing is not None:
                if existing.voucher_campaign_id != campaign.pk:
                    raise BusinessError("Idempotency-Key đã được dùng cho voucher khác")
                return existing, False

            now = timezone.now()
            if not campaign.is_active or not campaign.valid_from <= now <= campaign.valid_until:
                raise BusinessError("Voucher chưa đến thời gian lưu hoặc đã hết hạn")
            if campaign.remaining_quantity is not None and campaign.remaining_quantity <= 0:
                raise BusinessError("Voucher đã hết số lượng")
            claimed_count = UserVoucher.objects.filter(
                user=customer,
                voucher_campaign=campaign,
            ).count()
            if claimed_count >= campaign.usage_limit_per_user:
                raise BusinessError("Bạn đã đạt giới hạn lưu voucher này")

            user_voucher = UserVoucher.objects.create(
                user=customer,
                voucher_campaign=campaign,
                idempotency_key=normalized_key,
            )
            if campaign.remaining_quantity is not None:
                campaign.remaining_quantity -= 1
                campaign.save(update_fields=("remaining_quantity", "updated_at"))
            VoucherEvent.objects.create(
                user_voucher=user_voucher,
                action=VoucherEvent.Action.COLLECT,
            )
            return user_voucher, True

    @staticmethod
    def _codes_for_campaigns(campaigns: list[Voucher]) -> dict:
        platform = [
            campaign.code for campaign in campaigns if campaign.scope == Voucher.Scope.PLATFORM
        ]
        shops: dict[str, list[str]] = {}
        for campaign in campaigns:
            if campaign.scope == Voucher.Scope.SHOP and campaign.shop_id is not None:
                shops.setdefault(str(campaign.shop_id), []).append(campaign.code)
        return {"platform": platform, "shops": shops}

    @staticmethod
    def _ensure_stackable(campaigns: list[Voucher]) -> None:
        for index, left in enumerate(campaigns):
            for right in campaigns[index + 1 :]:
                if right.scope not in left.stackable_with or left.scope not in right.stackable_with:
                    raise BusinessError(f"Voucher {left.code} và {right.code} không được cộng dồn")

    @classmethod
    def evaluate(cls, *, cart, selected_item_ids: list | None = None) -> dict:
        customer = cart.user
        cls.release_expired_pending(customer=customer)
        now = timezone.now()
        auto_campaign_ids = (
            Voucher.objects.filter(
                collect_type=Voucher.CollectType.AUTO,
                is_active=True,
                valid_from__lte=now,
                valid_until__gte=now,
            )
            .filter(Q(remaining_quantity__isnull=True) | Q(remaining_quantity__gt=0))
            .values_list("pk", flat=True)
        )
        for campaign_id in auto_campaign_ids:
            try:
                cls.collect(
                    campaign_id=campaign_id,
                    user=customer,
                    idempotency_key=f"auto:{campaign_id}",
                )
            except BusinessError:
                pass
        owned = list(
            UserVoucher.objects.filter(
                user=customer,
                status=UserVoucher.Status.SAVED,
                voucher_campaign__is_active=True,
                voucher_campaign__valid_from__lte=now,
                voucher_campaign__valid_until__gte=now,
            ).select_related("voucher_campaign__shop", "voucher_campaign__applicable_category")
        )
        results = []
        best_id = None
        best_discount = Decimal("-1")
        for user_voucher in owned:
            campaign = user_voucher.voucher_campaign
            try:
                preview = PromotionCalculationService.calculate(
                    cart=cart,
                    selected_item_ids=selected_item_ids,
                    voucher_codes=cls._codes_for_campaigns([campaign]),
                )
                discount = Decimal(preview["discount"])
                eligible = True
                reason = ""
            except BusinessError as exc:
                preview = None
                discount = Decimal("0")
                eligible = False
                reason = str(exc)
                selected_total = sum(
                    Decimal(item.variant.sale_price) * item.quantity
                    for item in cart.items.filter(is_selected=True).select_related("variant")
                )
                missing = campaign.min_order_amount - selected_total
                if missing > 0:
                    reason = f"Mua thêm {int(missing):,}đ để áp dụng".replace(",", ".")
            results.append(
                {
                    "user_voucher": user_voucher,
                    "is_eligible": eligible,
                    "reason": reason,
                    "estimated_discount": discount,
                    "preview": preview,
                }
            )
            if eligible and discount > best_discount:
                best_discount = discount
                best_id = user_voucher.pk
        return {"results": results, "best_voucher_id": best_id}

    @classmethod
    def apply(
        cls,
        *,
        cart,
        user_voucher_ids: list,
        checkout_token: UUID | None = None,
        selected_item_ids: list | None = None,
    ) -> dict:
        customer = cart.user
        token = checkout_token or uuid4()
        with transaction.atomic():
            cls.release_expired_pending(customer=customer)
            deselected = list(
                UserVoucher.objects.select_for_update()
                .filter(
                    user=customer,
                    status=UserVoucher.Status.PENDING_USE,
                    checkout_token=token,
                )
                .exclude(pk__in=user_voucher_ids)
            )
            for item in deselected:
                item.status = UserVoucher.Status.SAVED
                item.checkout_token = None
                item.pending_expires_at = None
                item.save(
                    update_fields=(
                        "status",
                        "checkout_token",
                        "pending_expires_at",
                        "updated_at",
                    )
                )
                VoucherEvent.objects.create(
                    user_voucher=item,
                    action=VoucherEvent.Action.ROLLBACK,
                    metadata={"reason": "selection_changed"},
                )
            vouchers = list(
                UserVoucher.objects.select_for_update()
                # Only join the required, non-null campaign while locking. Joining
                # nullable campaign relations here produces an OUTER JOIN, which
                # PostgreSQL cannot combine with SELECT ... FOR UPDATE.
                .select_related("voucher_campaign")
                .filter(pk__in=user_voucher_ids, user=customer)
            )
            if len(vouchers) != len(set(user_voucher_ids)):
                raise BusinessError("Một hoặc nhiều voucher không thuộc tài khoản của bạn")
            for item in vouchers:
                if item.status == UserVoucher.Status.PENDING_USE and item.checkout_token == token:
                    continue
                if item.status != UserVoucher.Status.SAVED:
                    raise BusinessError(f"Voucher {item.voucher_campaign.code} đang được sử dụng")
            campaigns = [item.voucher_campaign for item in vouchers]
            cls._ensure_stackable(campaigns)
            preview = PromotionCalculationService.calculate(
                cart=cart,
                selected_item_ids=selected_item_ids,
                voucher_codes=cls._codes_for_campaigns(campaigns),
            )
            expires_at = timezone.now() + cls.PENDING_TTL
            for item in vouchers:
                item.status = UserVoucher.Status.PENDING_USE
                item.checkout_token = token
                item.pending_expires_at = expires_at
                item.save(
                    update_fields=(
                        "status",
                        "checkout_token",
                        "pending_expires_at",
                        "updated_at",
                    )
                )
                VoucherEvent.objects.create(
                    user_voucher=item,
                    action=VoucherEvent.Action.APPLY,
                    metadata={"checkout_token": str(token)},
                )
        return {**preview, "checkout_token": token, "pending_expires_at": expires_at}

    @classmethod
    def mark_used(cls, *, checkout_token: UUID, order_id: str) -> int:
        with transaction.atomic():
            vouchers = list(
                UserVoucher.objects.select_for_update().filter(
                    checkout_token=checkout_token,
                    status=UserVoucher.Status.PENDING_USE,
                )
            )
            now = timezone.now()
            for item in vouchers:
                item.status = UserVoucher.Status.USED
                item.used_at = now
                item.order_id = order_id
                item.pending_expires_at = None
                item.save(
                    update_fields=(
                        "status",
                        "used_at",
                        "order_id",
                        "pending_expires_at",
                        "updated_at",
                    )
                )
                VoucherEvent.objects.create(
                    user_voucher=item,
                    action=VoucherEvent.Action.USE,
                    order_id=order_id,
                )
            return len(vouchers)

    @classmethod
    def rollback(cls, *, checkout_token: UUID, reason: str) -> int:
        with transaction.atomic():
            vouchers = list(
                UserVoucher.objects.select_for_update().filter(
                    checkout_token=checkout_token,
                    status=UserVoucher.Status.PENDING_USE,
                )
            )
            for item in vouchers:
                item.status = UserVoucher.Status.SAVED
                item.checkout_token = None
                item.pending_expires_at = None
                item.save(
                    update_fields=(
                        "status",
                        "checkout_token",
                        "pending_expires_at",
                        "updated_at",
                    )
                )
                VoucherEvent.objects.create(
                    user_voucher=item,
                    action=VoucherEvent.Action.ROLLBACK,
                    metadata={"reason": reason},
                )
            return len(vouchers)

    @classmethod
    def expire_vouchers(cls) -> int:
        cls.release_expired_pending()
        vouchers = list(
            UserVoucher.objects.filter(
                status=UserVoucher.Status.SAVED,
                voucher_campaign__valid_until__lt=timezone.now(),
            )
        )
        if not vouchers:
            return 0
        UserVoucher.objects.filter(pk__in=[item.pk for item in vouchers]).update(
            status=UserVoucher.Status.EXPIRED,
            updated_at=timezone.now(),
        )
        VoucherEvent.objects.bulk_create(
            [
                VoucherEvent(user_voucher=item, action=VoucherEvent.Action.EXPIRE)
                for item in vouchers
            ]
        )
        return len(vouchers)


class FlashSaleService:
    @staticmethod
    def has_active_or_upcoming_sale() -> bool:
        """Tell price-bearing endpoints when cached product prices are unsafe."""
        return FlashSale.objects.filter(
            is_active=True,
            end_time__gte=timezone.now(),
        ).exists()

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

    @classmethod
    def commit_successful_purchase(cls, purchase_lines) -> list[FlashSaleItem]:
        """Atomically consume Flash Sale quota for successfully purchased variants.

        ``purchase_lines`` accepts objects or dictionaries containing
        ``variant_id`` and ``quantity``. The future Order/Payment completion
        transaction must call this hook exactly once after payment succeeds.
        The source page is intentionally irrelevant: matching is by variant.
        """
        quantities: dict[str, int] = {}
        for line in purchase_lines:
            variant_id = getattr(line, "variant_id", None)
            quantity = getattr(line, "quantity", None)
            if isinstance(line, dict):
                variant_id = line.get("variant_id")
                quantity = line.get("quantity")
            quantity = int(quantity or 0)
            if not variant_id or quantity <= 0:
                raise BusinessError("Dòng sản phẩm Flash Sale không hợp lệ")
            key = str(variant_id)
            quantities[key] = quantities.get(key, 0) + quantity

        if not quantities:
            return []

        now = timezone.now()
        with transaction.atomic():
            candidates = list(
                FlashSaleItem.objects.select_for_update()
                .select_related("flash_sale", "variant__product__shop")
                .filter(
                    variant_id__in=quantities,
                    flash_sale__is_active=True,
                    flash_sale__start_time__lte=now,
                    flash_sale__end_time__gte=now,
                    sold_count__lt=F("quota"),
                )
                .order_by("variant_id", "sale_price", "flash_sale__end_time", "id")
            )
            selected: dict[str, FlashSaleItem] = {}
            for candidate in candidates:
                selected.setdefault(str(candidate.variant_id), candidate)

            consumed: list[FlashSaleItem] = []
            for variant_id, quantity in quantities.items():
                item = selected.get(variant_id)
                # Ordinary products are valid purchase lines and consume no
                # Flash Sale quota.
                if item is None:
                    continue
                if item.sold_count + quantity > item.quota:
                    raise BusinessError(
                        f"Flash Sale của {item.variant.product.name} chỉ còn "
                        f"{item.remaining_quota} sản phẩm"
                    )
                item.sold_count += quantity
                item.save(update_fields=("sold_count", "updated_at"))
                consumed.append(item)

            if consumed:
                from apps.common.cache_utils import (
                    HOME_PAGE_CACHE_KEY,
                    invalidate_cache_keys_on_commit,
                    product_detail_cache_key,
                )

                keys = [HOME_PAGE_CACHE_KEY]
                for item in consumed:
                    product = item.variant.product
                    keys.extend(
                        (
                            product_detail_cache_key(slug=product.slug),
                            product_detail_cache_key(
                                slug=product.slug,
                                shop_slug=product.shop.slug,
                            ),
                        )
                    )
                invalidate_cache_keys_on_commit(*keys)
            return consumed


class PromotionCalculationService:
    """Side-effect-free cart pricing shared by preview and Sprint 07 checkout."""

    @staticmethod
    def _voucher_map(codes: list[str]) -> dict[str, Voucher]:
        normalized = [code.strip().upper() for code in codes if code and code.strip()]
        vouchers = Voucher.objects.select_related("shop", "applicable_category").filter(
            code__in=normalized
        )
        return {voucher.code: voucher for voucher in vouchers}

    @staticmethod
    def _eligible_amount(
        voucher: Voucher,
        shop_data: dict[str, Any],
        running_total: Decimal,
    ) -> Decimal:
        scope = voucher.applicable_scope or {}
        shop_ids = {int(value) for value in scope.get("shop_ids", [])}
        if shop_ids and shop_data["shop_id"] not in shop_ids:
            raise BusinessError(f"{voucher.code} không áp dụng cho shop này")
        category_ids = {str(value) for value in scope.get("category_ids", [])}
        if voucher.applicable_category_id:
            category_ids.add(str(voucher.applicable_category_id))
        if not category_ids:
            return running_total
        eligible_subtotal = sum(
            line["line_total"] for line in shop_data["items"] if line["category_id"] in category_ids
        )
        if eligible_subtotal <= 0:
            raise BusinessError(f"{voucher.code} không áp dụng cho sản phẩm đã chọn")
        return min(running_total, eligible_subtotal)

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
            if flash_item and item.quantity > flash_item.remaining_quota:
                raise BusinessError(
                    f"Flash Sale của {product.name} chỉ còn {flash_item.remaining_quota} sản phẩm",
                    errors={"item_id": [str(item.id)]},
                )
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
                eligible_amount = cls._eligible_amount(voucher, shop_data, running_total)
                discount = VoucherService.validate_and_apply(
                    code,
                    customer,
                    eligible_amount,
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
                eligible_amount = cls._eligible_amount(voucher, shop_data, running_total)
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
