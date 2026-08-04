from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.account.models import Address, Shop
from apps.cart.models import Cart, CartItem
from apps.cart.services import CartService
from apps.common.exceptions import BusinessError
from apps.inventory.services import StockService
from apps.promotion.models import VoucherUsage
from apps.promotion.services import PromotionCalculationService, VoucherService

from .exceptions import InvalidOrderTransition
from .models import (
    Order,
    OrderAddress,
    OrderCancellation,
    OrderItem,
    OrderStatusHistory,
    ShippingFeeRule,
    ShopOrder,
)
from .state_machine import OrderStateMachine


def _order_code(prefix: str) -> str:
    return f"{prefix}-{timezone.now():%Y%m%d}-{uuid4().hex[:10].upper()}"


def _queue(task, *args) -> None:
    transaction.on_commit(lambda: task.delay(*args))


class CheckoutService:
    PAYMENT_TTL = timedelta(minutes=15)
    DEFAULT_SHIPPING_FEE = Decimal("30000")

    @staticmethod
    def normalize_coupons(coupons: dict | None) -> dict:
        coupons = coupons or {}
        platform = coupons.get("platform") or []
        shops = coupons.get("shops", {}).copy()
        for key, value in coupons.items():
            if key.startswith("shop_") and key[5:]:
                shops[key[5:]] = value
        return {"platform": platform, "shops": shops}

    @classmethod
    def preview(cls, *, customer, cart_item_ids=None, coupons=None) -> dict:
        cart = Cart.objects.filter(user=customer).first()
        if cart is None:
            raise BusinessError("Giỏ hàng trống")
        pricing = PromotionCalculationService.calculate(
            cart=cart,
            selected_item_ids=cart_item_ids,
            voucher_codes=cls.normalize_coupons(coupons),
        )
        if not pricing["shops"]:
            raise BusinessError("Vui lòng chọn ít nhất một sản phẩm")
        shipping_total = Decimal("0")
        for shop_data in pricing["shops"]:
            rule = ShippingFeeRule.objects.filter(shop_id=shop_data["shop_id"]).first()
            fee = rule.calculate(shop_data["subtotal"]) if rule else cls.DEFAULT_SHIPPING_FEE
            shop_data["shipping_fee"] = fee
            shop_data["total"] += fee
            shipping_total += fee
        pricing["shipping_total"] = shipping_total
        pricing["total"] += shipping_total
        return pricing

    @classmethod
    def checkout(
        cls,
        *,
        customer,
        cart_item_ids,
        address_id,
        coupons,
        payment_method,
        idempotency_key,
        checkout_note="",
        shop_notes=None,
        shipping_methods=None,
    ) -> tuple[Order, str | None, bool]:
        key = str(idempotency_key or "").strip()
        if not key:
            raise BusinessError(
                "Thiếu Idempotency-Key",
                errors={"idempotency_key": ["Header Idempotency-Key là bắt buộc"]},
            )
        existing = Order.objects.filter(idempotency_key=key).first()
        if existing is not None:
            if existing.customer_id != customer.pk:
                raise BusinessError("Idempotency-Key đã được sử dụng", http_status=409)
            return existing, cls._existing_payment_url(existing), False
        if payment_method not in Order.PaymentMethod.values:
            raise BusinessError("Phương thức thanh toán không hợp lệ")
        shop_notes = shop_notes or {}
        shipping_methods = shipping_methods or {}
        address = Address.objects.filter(
            pk=address_id, user=customer.user, is_deleted=False
        ).first()
        if address is None:
            raise BusinessError("Địa chỉ giao hàng không hợp lệ", http_status=404)

        with transaction.atomic():
            cart = Cart.objects.select_for_update().filter(user=customer).first()
            if cart is None:
                raise BusinessError("Giỏ hàng trống")
            selected = CartItem.objects.select_for_update().filter(cart=cart)
            if cart_item_ids:
                selected = selected.filter(pk__in=cart_item_ids)
            else:
                selected = selected.filter(is_selected=True)
            selected_ids = [str(value) for value in selected.values_list("pk", flat=True)]
            if not selected_ids:
                raise BusinessError("Vui lòng chọn ít nhất một sản phẩm")
            pricing = cls.preview(customer=customer, cart_item_ids=selected_ids, coupons=coupons)
            item_map = {
                str(item.pk): item
                for item in selected.select_related(
                    "variant__product", "variant__shop"
                ).prefetch_related(
                    "variant__variant_attribute_links__attribute",
                    "variant__variant_attribute_links__attribute_value",
                    "variant__product__media",
                )
            }
            platform_discount = sum(
                discount["amount"]
                for shop in pricing["shops"]
                for discount in shop["discounts"]
                if discount["scope"] == "platform"
            )
            shop_discount = pricing["discount"] - platform_discount
            try:
                order = Order.objects.create(
                    order_code=_order_code("ORD"),
                    customer=customer,
                    subtotal=pricing["subtotal"],
                    platform_discount=platform_discount,
                    shop_discount_total=shop_discount,
                    shipping_total=pricing["shipping_total"],
                    grand_total=pricing["total"],
                    payment_method=payment_method,
                    payment_status=Order.PaymentStatus.PENDING,
                    idempotency_key=key,
                    checkout_note=checkout_note,
                    expires_at=(
                        timezone.now() + cls.PAYMENT_TTL
                        if payment_method == Order.PaymentMethod.VNPAY
                        else None
                    ),
                )
            except IntegrityError:
                order = Order.objects.get(idempotency_key=key)
                return order, cls._existing_payment_url(order), False
            OrderAddress.objects.create(
                order=order,
                recipient_name=address.recipient_name,
                recipient_phone=address.phone,
                province_name=address.province,
                district_name=address.district,
                ward_name=address.ward,
                address_line=address.detail_address,
            )
            for shop_data in pricing["shops"]:
                shop = Shop.objects.get(pk=shop_data["shop_id"])
                shipping_method = shipping_methods.get(
                    str(shop.pk), shipping_methods.get(shop.pk, {})
                )
                if not isinstance(shipping_method, dict):
                    shipping_method = {}
                shipping_code = str(shipping_method.get("code", "STANDARD")).strip().upper()
                if shipping_code != "STANDARD":
                    raise BusinessError(
                        "Phương thức vận chuyển không hợp lệ",
                        errors={"shipping_methods": [f"Shop {shop.pk} chỉ hỗ trợ STANDARD"]},
                    )
                shop_discount_amount = sum(
                    d["amount"] for d in shop_data["discounts"] if d["scope"] == "shop"
                )
                platform_amount = sum(
                    d["amount"] for d in shop_data["discounts"] if d["scope"] == "platform"
                )
                shop_order = ShopOrder.objects.create(
                    order=order,
                    shop=shop,
                    shop_order_code=_order_code("SORD"),
                    subtotal=shop_data["subtotal"],
                    shop_discount=shop_discount_amount,
                    platform_discount_allocated=platform_amount,
                    shipping_fee=shop_data["shipping_fee"],
                    total_amount=shop_data["total"],
                    shipping_method_code=shipping_code,
                    shipping_method_name="Giao hàng tiêu chuẩn (phí cố định)",
                    seller_note=str(shop_notes.get(str(shop.pk), shop_notes.get(shop.pk, "")))[
                        :2000
                    ],
                )
                OrderStatusHistory.objects.create(
                    shop_order=shop_order,
                    to_status=ShopOrder.FulfillmentStatus.PENDING_CONFIRMATION,
                    changed_by=customer.user,
                    reason="Checkout confirmed",
                )
                shop_allocated = Decimal("0")
                platform_allocated = Decimal("0")
                for index, line in enumerate(shop_data["items"]):
                    cart_item = item_map[line["item_id"]]
                    variant = cart_item.variant
                    if index == len(shop_data["items"]) - 1:
                        shop_share = shop_discount_amount - shop_allocated
                        platform_share = platform_amount - platform_allocated
                    elif shop_data["subtotal"]:
                        shop_share = (
                            shop_discount_amount * line["line_total"] / shop_data["subtotal"]
                        ).quantize(Decimal("1"))
                        platform_share = (
                            platform_amount * line["line_total"] / shop_data["subtotal"]
                        ).quantize(Decimal("1"))
                        shop_allocated += shop_share
                        platform_allocated += platform_share
                    else:
                        shop_share = platform_share = Decimal("0")
                    line_discount = shop_share + platform_share
                    attrs = {
                        link.attribute.name: link.attribute_value.display_value
                        or link.attribute_value.value
                        for link in variant.variant_attribute_links.all()
                    }
                    media = list(variant.product.media.all())
                    primary = next(
                        (entry for entry in media if entry.is_primary), media[0] if media else None
                    )
                    OrderItem.objects.create(
                        shop_order=shop_order,
                        product=variant.product,
                        variant=variant,
                        product_name=variant.product.name,
                        variant_name=variant.name or "",
                        sku=variant.sku,
                        variant_attributes=attrs,
                        product_image_url=primary.file_url if primary else None,
                        unit_original_price=variant.original_price,
                        unit_sale_price=line["unit_price"],
                        quantity=line["quantity"],
                        line_subtotal=line["line_total"],
                        shop_discount=shop_share,
                        platform_discount=platform_share,
                        line_total=max(Decimal("0"), line["line_total"] - line_discount),
                        cost_price_snapshot=variant.cost_price,
                    )
                    StockService.reserve_stock(
                        variant=variant,
                        quantity=line["quantity"],
                        order_reference=shop_order.reservation_reference,
                        user=customer.user,
                        expires_at=order.expires_at,
                    )
                for discount in shop_data["discounts"]:
                    VoucherService.validate_and_apply(
                        discount["code"],
                        customer,
                        shop_data["subtotal"],
                        shop=shop if discount["scope"] == "shop" else None,
                        commit=True,
                        order_reference=shop_order.shop_order_code,
                    )
                    VoucherUsage.objects.filter(
                        voucher__code=discount["code"],
                        user=customer,
                        order_reference=shop_order.shop_order_code,
                    ).update(discount_amount=discount["amount"])
            selected.delete()
            from .tasks import send_order_confirmation_notification

            _queue(send_order_confirmation_notification, str(order.pk))

        payment_url = None
        if payment_method == Order.PaymentMethod.VNPAY:
            from apps.payment.services import PaymentService

            payment_url = PaymentService.create_payment_intent(order)[1]
        return order, payment_url, True

    @staticmethod
    def _existing_payment_url(order) -> str | None:
        payment = (
            order.payments.filter(status="PENDING").order_by("-created_at").first()
            if hasattr(order, "payments")
            else None
        )
        if payment is None:
            return None
        from apps.payment.services import PaymentService

        return PaymentService.create_payment_intent(order)[1]


class OrderService:
    @staticmethod
    def _lock(shop_order) -> ShopOrder:
        return (
            ShopOrder.objects.select_for_update()
            .select_related("order", "shop")
            .get(pk=shop_order.pk)
        )

    @classmethod
    @transaction.atomic
    def confirm(cls, shop_order, actor) -> ShopOrder:
        current = cls._lock(shop_order)
        if (
            current.order.payment_method == Order.PaymentMethod.VNPAY
            and current.order.payment_status != Order.PaymentStatus.PAID
        ):
            raise BusinessError("Đơn VNPay chưa được thanh toán", http_status=409)
        StockService.commit_stock(current.reservation_reference, actor)
        return cls._transition_locked(current, ShopOrder.FulfillmentStatus.CONFIRMED, actor)

    @classmethod
    @transaction.atomic
    def transition_status(cls, shop_order, target_status, actor, reason=None) -> ShopOrder:
        current = cls._lock(shop_order)
        return cls._transition_locked(current, target_status, actor, reason)

    @staticmethod
    def _transition_locked(shop_order, target, actor, reason=None) -> ShopOrder:
        source = shop_order.fulfillment_status
        if not OrderStateMachine.can_transition(source, target, actor.role):
            raise InvalidOrderTransition(source, target)
        now = timezone.now()
        shop_order.fulfillment_status = target
        update_fields = ["fulfillment_status", "updated_at"]
        if target == ShopOrder.FulfillmentStatus.CONFIRMED:
            shop_order.confirmed_at = now
            update_fields.append("confirmed_at")
        elif target == ShopOrder.FulfillmentStatus.DELIVERED:
            shop_order.delivered_at = now
            update_fields.append("delivered_at")
            if shop_order.order.payment_method == Order.PaymentMethod.COD:
                shop_order.cod_collected_at = now
                update_fields.append("cod_collected_at")
        elif target == ShopOrder.FulfillmentStatus.COMPLETED:
            shop_order.completed_at = now
            update_fields.append("completed_at")
        shop_order.save(update_fields=update_fields)
        OrderStatusHistory.objects.create(
            shop_order=shop_order,
            from_status=source,
            to_status=target,
            changed_by=actor,
            reason=reason or "",
        )
        from .tasks import send_order_status_change_notification

        _queue(send_order_status_change_notification, str(shop_order.pk), target)
        return shop_order

    @classmethod
    @transaction.atomic
    def cancel(cls, shop_order, actor, reason_code, reason_detail="") -> ShopOrder:
        current = cls._lock(shop_order)
        source = current.fulfillment_status
        if not OrderStateMachine.can_transition(
            source, ShopOrder.FulfillmentStatus.CANCELLED, actor.role
        ):
            raise InvalidOrderTransition(source, ShopOrder.FulfillmentStatus.CANCELLED)
        cancellation, _ = OrderCancellation.objects.get_or_create(
            shop_order=current,
            defaults={
                "requested_by": actor,
                "reason_code": reason_code,
                "reason_detail": reason_detail,
            },
        )
        if cancellation.stock_restored_at is None:
            if source == ShopOrder.FulfillmentStatus.PENDING_CONFIRMATION:
                StockService.release_stock(current.reservation_reference, actor)
            else:
                for item in current.items.select_related("variant").order_by("variant_id"):
                    if item.variant_id:
                        StockService.adjust_stock(
                            variant=item.variant,
                            quantity=item.quantity,
                            reference=f"cancel:{current.shop_order_code}",
                            user=actor,
                        )
            cancellation.stock_restored_at = timezone.now()
        if cancellation.voucher_released_at is None:
            VoucherUsage.objects.filter(order_reference=current.shop_order_code).delete()
            cancellation.voucher_released_at = timezone.now()
        cancellation.save(update_fields=("stock_restored_at", "voucher_released_at"))
        if current.order.payment_status == Order.PaymentStatus.PAID:
            from apps.payment.services import PaymentService

            PaymentService.refund(current, reason_detail or reason_code, process_provider=False)
        return cls._transition_locked(
            current, ShopOrder.FulfillmentStatus.CANCELLED, actor, reason_detail or reason_code
        )

    @staticmethod
    def reorder(order, customer) -> list[dict]:
        cart = CartService.get_or_create_customer_cart(customer.user)
        skipped = []
        for item in OrderItem.objects.filter(shop_order__order=order).select_related(
            "variant__product", "variant__shop"
        ):
            if item.variant is None:
                skipped.append({"sku": item.sku, "reason": "variant_deleted"})
                continue
            try:
                CartService.add_item(cart, item.variant, item.quantity)
            except BusinessError as exc:
                skipped.append({"sku": item.sku, "reason": str(exc)})
        return skipped
