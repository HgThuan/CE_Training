from collections import OrderedDict
from collections.abc import Iterable
from decimal import Decimal

from django.db import transaction

from apps.account.models import CustomerProfile
from apps.cart.models import Cart, CartItem
from apps.common.exceptions import BusinessError
from apps.product.models import ProductVariant


class CartService:
    """All cart mutations and price/stock revalidation live in this service."""

    @staticmethod
    def get_or_create_customer_cart(user) -> Cart:
        if not user.is_authenticated:
            raise BusinessError("Vui lòng đăng nhập để đồng bộ giỏ hàng", http_status=401)
        customer, _ = CustomerProfile.objects.get_or_create(user=user)
        cart, _ = Cart.objects.get_or_create(user=customer)
        return cart

    @staticmethod
    def _available_stock(variant: ProductVariant) -> int:
        return variant.available_stock

    @staticmethod
    def _price(variant: ProductVariant):
        from apps.promotion.services import FlashSaleService

        return FlashSaleService.get_active_price(variant)

    @staticmethod
    def _flash_item(variant: ProductVariant):
        from apps.promotion.services import FlashSaleService

        return FlashSaleService.get_active_item(variant)

    @classmethod
    def _validate_flash_quota(cls, variant: ProductVariant, quantity: int) -> None:
        flash_item = cls._flash_item(variant)
        if flash_item and quantity > flash_item.remaining_quota:
            raise BusinessError(
                "Số lượng vượt quá suất Flash Sale còn lại",
                errors={"quantity": [f"Chỉ còn {flash_item.remaining_quota} suất Flash Sale"]},
            )

    @classmethod
    def add_item(
        cls,
        cart: Cart,
        variant: ProductVariant,
        quantity: int,
        *,
        is_selected: bool = True,
    ) -> CartItem:
        """Add/increment an item without reserving inventory."""
        if quantity <= 0:
            raise BusinessError(
                "Số lượng phải lớn hơn 0",
                errors={"quantity": ["Giá trị không hợp lệ"]},
            )
        if (
            not variant.is_active
            or variant.is_deleted
            or variant.product.is_deleted
            or variant.product.status != variant.product.Status.APPROVED
            or variant.shop.is_deleted
            or variant.shop.status != variant.shop.Status.APPROVED
        ):
            raise BusinessError("Sản phẩm không còn khả dụng")

        with transaction.atomic():
            Cart.objects.select_for_update().get(pk=cart.pk)
            item = (
                CartItem.objects.select_for_update()
                .filter(cart=cart, variant=variant)
                .first()
            )
            target_quantity = quantity + (item.quantity if item else 0)
            available_stock = cls._available_stock(variant)
            if target_quantity > available_stock:
                raise BusinessError(
                    "Số lượng vượt quá tồn kho khả dụng",
                    errors={"quantity": [f"Chỉ còn {available_stock} sản phẩm"]},
                )
            cls._validate_flash_quota(variant, target_quantity)
            if item:
                item.quantity = target_quantity
                item.is_selected = is_selected
                item.save(update_fields=("quantity", "is_selected", "updated_at"))
                return item
            return CartItem.objects.create(
                cart=cart,
                variant=variant,
                quantity=quantity,
                is_selected=is_selected,
                unit_price_snapshot=cls._price(variant),
            )

    @classmethod
    def update_item(
        cls,
        item: CartItem,
        *,
        quantity: int | None = None,
        is_selected: bool | None = None,
    ) -> CartItem:
        if quantity is not None:
            if quantity <= 0:
                raise BusinessError("Số lượng phải lớn hơn 0")
            available_stock = cls._available_stock(item.variant)
            if quantity > available_stock:
                raise BusinessError(
                    "Số lượng vượt quá tồn kho khả dụng",
                    errors={"quantity": [f"Chỉ còn {available_stock} sản phẩm"]},
                )
            cls._validate_flash_quota(item.variant, quantity)
            item.quantity = quantity
        if is_selected is not None:
            item.is_selected = is_selected
        item.save(update_fields=("quantity", "is_selected", "updated_at"))
        return item

    @classmethod
    def merge_guest_cart(cls, guest_items: Iterable[dict], user) -> Cart:
        """Merge a localStorage payload into the authenticated cart atomically.

        Each payload item is ``{"variant_id": UUID, "quantity": int}``.
        Inventory is validated and no stock reservation is created.
        """
        cart = cls.get_or_create_customer_cart(user)
        normalized: OrderedDict[str, int] = OrderedDict()
        for raw in guest_items:
            variant_id = str(raw["variant_id"])
            quantity = int(raw["quantity"])
            if quantity <= 0:
                raise BusinessError("Số lượng giỏ khách phải lớn hơn 0")
            normalized[variant_id] = normalized.get(variant_id, 0) + quantity

        variants = {
            str(variant.id): variant
            for variant in ProductVariant.objects.select_related("product", "shop").filter(
                id__in=normalized.keys()
            )
        }
        if len(variants) != len(normalized):
            raise BusinessError("Một hoặc nhiều biến thể không tồn tại")

        with transaction.atomic():
            Cart.objects.select_for_update().get(pk=cart.pk)
            existing = {
                str(item.variant_id): item
                for item in CartItem.objects.select_for_update().filter(
                    cart=cart, variant_id__in=normalized.keys()
                )
            }
            for variant_id, guest_quantity in normalized.items():
                variant = variants[variant_id]
                current = existing.get(variant_id)
                target = guest_quantity + (current.quantity if current else 0)
                if target > cls._available_stock(variant):
                    raise BusinessError(
                        "Không thể gộp giỏ vì số lượng vượt tồn kho",
                        errors={"variant_id": [variant_id]},
                    )
                cls._validate_flash_quota(variant, target)
                if current:
                    current.quantity = target
                    current.save(update_fields=("quantity", "updated_at"))
                else:
                    CartItem.objects.create(
                        cart=cart,
                        variant=variant,
                        quantity=guest_quantity,
                        unit_price_snapshot=cls._price(variant),
                    )
        return cart

    @classmethod
    def get_cart_summary(cls, cart: Cart) -> dict:
        """Return a shop-grouped, current-price/current-stock cart snapshot."""
        items = cart.items.select_related(
            "variant__inventory_balance",
            "variant__product__shop",
        ).prefetch_related("variant__product__media")
        shops: OrderedDict[int, dict] = OrderedDict()
        selected_subtotal = Decimal("0")
        total_quantity = 0
        selected_quantity = 0

        from apps.promotion.services import FlashSaleService

        for item in items:
            variant = item.variant
            product = variant.product
            shop = variant.shop
            stock = cls._available_stock(variant)
            flash_item = FlashSaleService.get_active_item(variant)
            current_price = flash_item.sale_price if flash_item else variant.sale_price
            price_changed = item.unit_price_snapshot != current_price
            is_valid = (
                variant.is_active
                and not variant.is_deleted
                and product.status == product.Status.APPROVED
                and not product.is_deleted
                and shop.status == shop.Status.APPROVED
                and not shop.is_deleted
                and item.quantity <= stock
                and (flash_item is None or item.quantity <= flash_item.remaining_quota)
            )
            media = list(product.media.all())
            primary = next(
                (entry for entry in media if entry.is_primary),
                media[0] if media else None,
            )
            line_total = current_price * item.quantity
            item_data = {
                "id": str(item.id),
                "variant_id": str(variant.id),
                "variant_sku": variant.sku,
                "variant_name": variant.name,
                "product_id": str(product.id),
                "product_name": product.name,
                "product_slug": product.slug,
                "primary_image": primary.file_url if primary else None,
                "quantity": item.quantity,
                "is_selected": item.is_selected,
                "unit_price_snapshot": item.unit_price_snapshot,
                "current_price": current_price,
                "regular_price": variant.sale_price,
                "is_flash_sale": flash_item is not None,
                "flash_sale_ends_at": (
                    flash_item.flash_sale.end_time if flash_item else None
                ),
                "remaining_flash_quota": flash_item.remaining_quota if flash_item else None,
                "line_total": line_total,
                "available_stock": stock,
                "price_changed": price_changed,
                "is_valid": is_valid,
            }
            shop_data = shops.setdefault(
                shop.id,
                {
                    "shop_id": shop.id,
                    "shop_name": shop.name,
                    "shop_slug": shop.slug,
                    "logo_url": shop.logo_url,
                    "items": [],
                    "subtotal": Decimal("0"),
                },
            )
            shop_data["items"].append(item_data)
            total_quantity += item.quantity
            if item.is_selected:
                selected_quantity += item.quantity
                if is_valid:
                    shop_data["subtotal"] += line_total
                    selected_subtotal += line_total

        return {
            "id": str(cart.id),
            "total_items": total_quantity,
            "total_selected_items": selected_quantity,
            "shops": list(shops.values()),
            "subtotal": selected_subtotal,
            "updated_at": cart.updated_at,
        }

    @staticmethod
    def preview_checkout(
        cart: Cart,
        selected_item_ids: list | None,
        voucher_codes: dict | None,
    ) -> dict:
        """Dry-run checkout preview; creates no reservation or voucher usage."""
        from apps.promotion.services import PromotionCalculationService

        return PromotionCalculationService.calculate(
            cart=cart,
            selected_item_ids=selected_item_ids,
            voucher_codes=voucher_codes or {},
        )
