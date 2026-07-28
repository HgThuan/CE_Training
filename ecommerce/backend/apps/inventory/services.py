from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.account.models import Shop, User
from apps.common.exceptions import BusinessError
from apps.product.models import Product, ProductVariant

from .exceptions import InsufficientStockError
from .models import (
    InventoryBalance,
    StockAlert,
    StockEntry,
    StockEntryItem,
    StockMovement,
    StockOutEntry,
    StockOutEntryItem,
    StockReservation,
)


def _actor_is_active(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and not getattr(user, "is_deleted", True)
    )


def _get_seller_shop(user) -> Shop:
    if not _actor_is_active(user) or getattr(user, "role", None) != User.Role.SELLER:
        raise BusinessError("Chỉ Seller mới có quyền quản lý tồn kho", http_status=403)
    shop = Shop.objects.filter(owner=user, is_deleted=False).first()
    if shop is None:
        raise BusinessError("Không tìm thấy gian hàng của Seller", http_status=404)
    return shop


def _validate_actor(user) -> None:
    if not _actor_is_active(user):
        raise BusinessError("Người thao tác không hợp lệ", http_status=403)


class StockService:
    """The only application service allowed to mutate balances and append movements."""

    @staticmethod
    def _owned_variants(*, shop: Shop, variant_ids: list) -> dict:
        normalized_ids = [str(variant_id) for variant_id in variant_ids]
        if not normalized_ids:
            raise BusinessError(
                "Phiếu kho cần ít nhất một dòng hàng",
                errors={"items": ["Danh sách sản phẩm không được để trống"]},
            )
        if len(normalized_ids) != len(set(normalized_ids)):
            raise BusinessError(
                "Một biến thể chỉ được xuất hiện một lần trong phiếu",
                errors={"items": ["Danh sách biến thể bị trùng"]},
            )
        variants = {
            str(variant.pk): variant
            for variant in ProductVariant.objects.select_related("product", "shop").filter(
                pk__in=normalized_ids,
                shop=shop,
                product__shop=shop,
                is_deleted=False,
                product__is_deleted=False,
            )
        }
        if len(variants) != len(normalized_ids):
            raise BusinessError(
                "Phiếu chứa biến thể không thuộc gian hàng",
                errors={"items": ["Một hoặc nhiều biến thể không hợp lệ"]},
                http_status=403,
            )
        return variants

    @staticmethod
    def _lock_balances(variants: list[ProductVariant]) -> dict[str, InventoryBalance]:
        ordered_variants = sorted(variants, key=lambda item: str(item.pk))
        InventoryBalance.objects.bulk_create(
            [
                InventoryBalance(
                    variant=variant,
                    available_stock=variant.stock_quantity,
                    reserved_stock=0,
                )
                for variant in ordered_variants
            ],
            ignore_conflicts=True,
        )
        return {
            str(balance.variant_id): balance
            for balance in InventoryBalance.objects.select_for_update()
            .select_related("variant__product", "variant__shop__owner")
            .filter(variant__in=ordered_variants)
            .order_by("variant_id")
        }

    @staticmethod
    def _apply_delta(
        *,
        balance: InventoryBalance,
        bucket: str,
        delta: int,
        insufficient_error: bool = False,
    ) -> int:
        if bucket not in {
            StockMovement.Bucket.AVAILABLE,
            StockMovement.Bucket.RESERVED,
        }:
            raise ValueError("Unknown inventory bucket")
        field = (
            "available_stock"
            if bucket == StockMovement.Bucket.AVAILABLE
            else "reserved_stock"
        )
        filters = {"pk": balance.pk}
        if delta < 0:
            filters[f"{field}__gte"] = -delta
        updated = InventoryBalance.objects.filter(**filters).update(
            **{
                field: F(field) + delta,
                "updated_at": timezone.now(),
            }
        )
        if updated != 1:
            if insufficient_error:
                raise InsufficientStockError()
            raise BusinessError(
                "Dữ liệu tồn kho không nhất quán",
                errors={field: ["Số dư bucket không đủ để thực hiện thao tác"]},
                http_status=409,
            )
        balance.refresh_from_db(fields=[field, "updated_at"])
        return getattr(balance, field)

    @staticmethod
    def _append_movement(
        *,
        balance: InventoryBalance,
        movement_type: str,
        bucket: str,
        quantity: int,
        reference_type: str,
        reference_id: str,
        user,
        note: str = "",
    ) -> StockMovement | None:
        if quantity == 0:
            return None
        balance_after = (
            balance.available_stock
            if bucket == StockMovement.Bucket.AVAILABLE
            else balance.reserved_stock
        )
        return StockMovement.objects.create(
            variant=balance.variant,
            movement_type=movement_type,
            bucket=bucket,
            quantity=quantity,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=str(reference_id),
            note=note,
            created_by=user,
        )

    @staticmethod
    def _entry_items(*, shop: Shop, raw_items: list[dict]) -> list[dict]:
        variants = StockService._owned_variants(
            shop=shop,
            variant_ids=[item.get("variant_id") for item in raw_items],
        )
        normalized = []
        for item in raw_items:
            try:
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError) as exc:
                raise BusinessError(
                    "Số lượng nhập không hợp lệ",
                    errors={"items": ["Số lượng nhập phải là số nguyên dương"]},
                ) from exc
            try:
                unit_cost = Decimal(str(item.get("unit_cost")))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise BusinessError(
                    "Giá nhập không hợp lệ",
                    errors={"items": ["Giá nhập phải là số không âm"]},
                ) from exc
            if quantity <= 0 or unit_cost < 0:
                raise BusinessError(
                    "Dòng phiếu nhập không hợp lệ",
                    errors={"items": ["Số lượng phải dương và giá nhập không được âm"]},
                )
            normalized.append(
                {
                    "variant": variants[str(item["variant_id"])],
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                }
            )
        return normalized

    @staticmethod
    @transaction.atomic
    def create_stock_entry(*, user, data: dict) -> StockEntry:
        shop = _get_seller_shop(user)
        supplier_name = str(data.get("supplier_name", "")).strip()
        if not supplier_name:
            raise BusinessError(
                "Nhà cung cấp là bắt buộc",
                errors={"supplier_name": ["Trường này không được để trống"]},
            )
        items = StockService._entry_items(shop=shop, raw_items=data.get("items") or [])
        entry = StockEntry.objects.create(
            shop=shop,
            supplier_name=supplier_name,
            note=str(data.get("note", "")).strip(),
            created_by=user,
        )
        StockEntryItem.objects.bulk_create(
            [StockEntryItem(stock_entry=entry, **item) for item in items]
        )
        return entry

    @staticmethod
    @transaction.atomic
    def update_stock_entry(*, stock_entry_id, user, data: dict) -> StockEntry:
        entry = (
            StockEntry.objects.select_for_update()
            .filter(pk=stock_entry_id, shop__owner=user, shop__is_deleted=False)
            .first()
        )
        if entry is None:
            raise BusinessError("Không tìm thấy phiếu nhập kho", http_status=404)
        if entry.status != StockEntry.Status.DRAFT:
            raise BusinessError("Không thể sửa phiếu nhập đã xác nhận", http_status=409)

        update_fields = []
        if "supplier_name" in data:
            supplier_name = str(data["supplier_name"]).strip()
            if not supplier_name:
                raise BusinessError(
                    "Nhà cung cấp là bắt buộc",
                    errors={"supplier_name": ["Trường này không được để trống"]},
                )
            entry.supplier_name = supplier_name
            update_fields.append("supplier_name")
        if "note" in data:
            entry.note = str(data["note"]).strip()
            update_fields.append("note")
        if update_fields:
            entry.save(update_fields=[*update_fields, "updated_at"])
        if "items" in data:
            items = StockService._entry_items(
                shop=entry.shop,
                raw_items=data.get("items") or [],
            )
            entry.items.all().delete()
            StockEntryItem.objects.bulk_create(
                [StockEntryItem(stock_entry=entry, **item) for item in items]
            )
        return StockService._stock_entry_with_relations(entry.pk)

    @staticmethod
    def _stock_entry_with_relations(stock_entry_id) -> StockEntry:
        return (
            StockEntry.objects.select_related("shop", "created_by", "confirmed_by")
            .prefetch_related("items__variant__product")
            .get(pk=stock_entry_id)
        )

    @staticmethod
    @transaction.atomic
    def confirm_stock_entry(stock_entry_id, user) -> StockEntry:
        shop = _get_seller_shop(user)
        entry = (
            StockEntry.objects.select_for_update()
            .filter(pk=stock_entry_id, shop=shop)
            .first()
        )
        if entry is None:
            raise BusinessError("Không tìm thấy phiếu nhập kho", http_status=404)
        if entry.status == StockEntry.Status.CONFIRMED:
            raise BusinessError("Phiếu nhập đã được xác nhận", http_status=409)

        items = list(
            entry.items.select_related("variant__product", "variant__shop")
            .order_by("variant_id")
        )
        if not items:
            raise BusinessError("Không thể xác nhận phiếu nhập không có dòng hàng")
        variants = StockService._owned_variants(
            shop=shop,
            variant_ids=[item.variant_id for item in items],
        )
        balances = StockService._lock_balances(list(variants.values()))
        transitions = []
        for item in items:
            balance = balances[str(item.variant_id)]
            was_out_of_stock = balance.available_stock == 0
            StockService._apply_delta(
                balance=balance,
                bucket=StockMovement.Bucket.AVAILABLE,
                delta=item.quantity,
            )
            StockService._append_movement(
                balance=balance,
                movement_type=StockMovement.MovementType.IN,
                bucket=StockMovement.Bucket.AVAILABLE,
                quantity=item.quantity,
                reference_type=StockMovement.ReferenceType.STOCK_ENTRY,
                reference_id=str(entry.pk),
                user=user,
                note=entry.note,
            )
            if was_out_of_stock and balance.available_stock > 0:
                transitions.append(balance)

        now = timezone.now()
        StockEntry.objects.filter(pk=entry.pk).update(
            status=StockEntry.Status.CONFIRMED,
            confirmed_by=user,
            confirmed_at=now,
            updated_at=now,
        )
        from .signals import stock_became_available

        for balance in transitions:
            stock_became_available(
                variant=balance.variant,
                available_stock=balance.available_stock,
            )
        return StockService._stock_entry_with_relations(entry.pk)

    @staticmethod
    def _out_items(*, shop: Shop, entry_type: str, raw_items: list[dict]) -> list[dict]:
        variants = StockService._owned_variants(
            shop=shop,
            variant_ids=[item.get("variant_id") for item in raw_items],
        )
        normalized = []
        for item in raw_items:
            try:
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError) as exc:
                raise BusinessError(
                    "Số lượng xuất/kiểm kê không hợp lệ",
                    errors={"items": ["Số lượng phải là số nguyên"]},
                ) from exc
            if quantity < 0 or (
                entry_type == StockOutEntry.EntryType.OUT and quantity == 0
            ):
                raise BusinessError(
                    "Dòng phiếu xuất/kiểm kê không hợp lệ",
                    errors={
                        "items": [
                            "Phiếu xuất cần số lượng dương; tồn kiểm kê có thể bằng 0"
                        ]
                    },
                )
            normalized.append(
                {
                    "variant": variants[str(item["variant_id"])],
                    "quantity": quantity,
                }
            )
        return normalized

    @staticmethod
    @transaction.atomic
    def create_stock_out_entry(*, user, data: dict) -> StockOutEntry:
        shop = _get_seller_shop(user)
        reason = str(data.get("reason", "")).strip()
        entry_type = data.get("entry_type")
        if entry_type not in StockOutEntry.EntryType.values:
            raise BusinessError(
                "Loại phiếu không hợp lệ",
                errors={"entry_type": ["Chọn xuất kho hoặc kiểm kê"]},
            )
        if not reason:
            raise BusinessError(
                "Lý do là bắt buộc",
                errors={"reason": ["Trường này không được để trống"]},
            )
        items = StockService._out_items(
            shop=shop,
            entry_type=entry_type,
            raw_items=data.get("items") or [],
        )
        entry = StockOutEntry.objects.create(
            shop=shop,
            entry_type=entry_type,
            reason=reason,
            created_by=user,
        )
        StockOutEntryItem.objects.bulk_create(
            [StockOutEntryItem(stock_out_entry=entry, **item) for item in items]
        )
        return entry

    @staticmethod
    def _stock_out_with_relations(stock_out_entry_id) -> StockOutEntry:
        return (
            StockOutEntry.objects.select_related("shop", "created_by", "confirmed_by")
            .prefetch_related("items__variant__product")
            .get(pk=stock_out_entry_id)
        )

    @staticmethod
    @transaction.atomic
    def update_stock_out_entry(*, stock_out_entry_id, user, data: dict) -> StockOutEntry:
        entry = (
            StockOutEntry.objects.select_for_update()
            .filter(pk=stock_out_entry_id, shop__owner=user, shop__is_deleted=False)
            .first()
        )
        if entry is None:
            raise BusinessError("Không tìm thấy phiếu xuất/kiểm kê", http_status=404)
        if entry.status != StockOutEntry.Status.DRAFT:
            raise BusinessError("Không thể sửa phiếu đã xác nhận", http_status=409)

        entry_type = data.get("entry_type", entry.entry_type)
        reason = str(data.get("reason", entry.reason)).strip()
        if entry_type not in StockOutEntry.EntryType.values or not reason:
            raise BusinessError("Loại phiếu và lý do phải hợp lệ")
        items = None
        if "items" in data:
            items = StockService._out_items(
                shop=entry.shop,
                entry_type=entry_type,
                raw_items=data.get("items") or [],
            )
        entry.entry_type = entry_type
        entry.reason = reason
        entry.save(update_fields=["entry_type", "reason", "updated_at"])
        if items is not None:
            entry.items.all().delete()
            StockOutEntryItem.objects.bulk_create(
                [StockOutEntryItem(stock_out_entry=entry, **item) for item in items]
            )
        return StockService._stock_out_with_relations(entry.pk)

    @staticmethod
    @transaction.atomic
    def confirm_stock_out(stock_out_entry_id, user) -> StockOutEntry:
        shop = _get_seller_shop(user)
        entry = (
            StockOutEntry.objects.select_for_update()
            .filter(pk=stock_out_entry_id, shop=shop)
            .first()
        )
        if entry is None:
            raise BusinessError("Không tìm thấy phiếu xuất/kiểm kê", http_status=404)
        if entry.status == StockOutEntry.Status.CONFIRMED:
            raise BusinessError("Phiếu xuất/kiểm kê đã được xác nhận", http_status=409)

        items = list(
            entry.items.select_related("variant__product", "variant__shop")
            .order_by("variant_id")
        )
        if not items:
            raise BusinessError("Không thể xác nhận phiếu không có dòng hàng")
        variants = StockService._owned_variants(
            shop=shop,
            variant_ids=[item.variant_id for item in items],
        )
        balances = StockService._lock_balances(list(variants.values()))
        low_stock_transitions = []
        for item in items:
            balance = balances[str(item.variant_id)]
            previous = balance.available_stock
            if entry.entry_type == StockOutEntry.EntryType.OUT:
                if item.quantity <= 0:
                    raise BusinessError("Số lượng xuất phải lớn hơn 0")
                delta = -item.quantity
                movement_type = StockMovement.MovementType.OUT
                reference_type = StockMovement.ReferenceType.STOCK_OUT
            else:
                delta = item.quantity - previous
                movement_type = StockMovement.MovementType.ADJUSTMENT
                reference_type = StockMovement.ReferenceType.ADJUSTMENT
            StockService._apply_delta(
                balance=balance,
                bucket=StockMovement.Bucket.AVAILABLE,
                delta=delta,
                insufficient_error=delta < 0,
            )
            StockService._append_movement(
                balance=balance,
                movement_type=movement_type,
                bucket=StockMovement.Bucket.AVAILABLE,
                quantity=delta,
                reference_type=reference_type,
                reference_id=str(entry.pk),
                user=user,
                note=entry.reason,
            )
            if (
                delta < 0
                and previous > balance.low_stock_threshold
                and balance.available_stock <= balance.low_stock_threshold
            ):
                low_stock_transitions.append(balance)

        now = timezone.now()
        StockOutEntry.objects.filter(pk=entry.pk).update(
            status=StockOutEntry.Status.CONFIRMED,
            confirmed_by=user,
            confirmed_at=now,
            updated_at=now,
        )
        from .signals import stock_reached_low_threshold

        for balance in low_stock_transitions:
            stock_reached_low_threshold(balance=balance)
        return StockService._stock_out_with_relations(entry.pk)

    @staticmethod
    @transaction.atomic
    def reserve_stock(
        variant,
        quantity,
        order_reference,
        user,
        expires_at=None,
    ) -> StockReservation:
        _validate_actor(user)
        try:
            requested_quantity = int(quantity)
        except (TypeError, ValueError) as exc:
            raise BusinessError("Số lượng giữ kho phải là số nguyên dương") from exc
        reference = str(order_reference).strip()
        if requested_quantity <= 0 or not reference:
            raise BusinessError("Số lượng giữ kho và mã tham chiếu phải hợp lệ")

        locked_variant = (
            ProductVariant.objects.select_related("product", "shop")
            .filter(
                pk=getattr(variant, "pk", variant),
                is_deleted=False,
                product__is_deleted=False,
            )
            .first()
        )
        if locked_variant is None:
            raise BusinessError("Không tìm thấy biến thể", http_status=404)
        balance = StockService._lock_balances([locked_variant])[str(locked_variant.pk)]
        existing = (
            StockReservation.objects.select_for_update()
            .filter(variant=locked_variant, order_reference=reference)
            .first()
        )
        if existing is not None:
            if existing.quantity != requested_quantity:
                raise BusinessError(
                    "Retry giữ kho không khớp dữ liệu ban đầu",
                    errors={"quantity": ["Không thể đổi số lượng với cùng order_reference"]},
                    http_status=409,
                )
            return existing

        StockService._apply_delta(
            balance=balance,
            bucket=StockMovement.Bucket.AVAILABLE,
            delta=-requested_quantity,
            insufficient_error=True,
        )
        StockService._append_movement(
            balance=balance,
            movement_type=StockMovement.MovementType.RESERVE,
            bucket=StockMovement.Bucket.AVAILABLE,
            quantity=-requested_quantity,
            reference_type=StockMovement.ReferenceType.ORDER,
            reference_id=reference,
            user=user,
        )
        StockService._apply_delta(
            balance=balance,
            bucket=StockMovement.Bucket.RESERVED,
            delta=requested_quantity,
        )
        StockService._append_movement(
            balance=balance,
            movement_type=StockMovement.MovementType.RESERVE,
            bucket=StockMovement.Bucket.RESERVED,
            quantity=requested_quantity,
            reference_type=StockMovement.ReferenceType.ORDER,
            reference_id=reference,
            user=user,
        )
        try:
            return StockReservation.objects.create(
                variant=locked_variant,
                order_reference=reference,
                quantity=requested_quantity,
                expires_at=expires_at,
            )
        except IntegrityError as exc:
            raise BusinessError(
                "Reservation trùng order_reference",
                http_status=409,
            ) from exc

    @staticmethod
    def release_stock(order_reference, user, variant=None) -> list[StockReservation]:
        return StockService._close_reservations(
            order_reference=order_reference,
            user=user,
            variant=variant,
            target_status=StockReservation.Status.RELEASED,
        )

    @staticmethod
    def commit_stock(order_reference, user, variant=None) -> list[StockReservation]:
        return StockService._close_reservations(
            order_reference=order_reference,
            user=user,
            variant=variant,
            target_status=StockReservation.Status.COMMITTED,
        )

    @staticmethod
    @transaction.atomic
    def _close_reservations(
        *,
        order_reference,
        user,
        variant,
        target_status: str,
    ) -> list[StockReservation]:
        _validate_actor(user)
        reference = str(order_reference).strip()
        if not reference:
            raise BusinessError("Mã tham chiếu đơn hàng là bắt buộc")
        base_query = StockReservation.objects.filter(order_reference=reference)
        if variant is not None:
            base_query = base_query.filter(variant_id=getattr(variant, "pk", variant))
        variant_ids = list(
            base_query.order_by("variant_id").values_list("variant_id", flat=True).distinct()
        )
        if not variant_ids:
            return []
        variants = list(
            ProductVariant.objects.select_related("product", "shop")
            .filter(pk__in=variant_ids)
            .order_by("pk")
        )
        balances = StockService._lock_balances(variants)
        reservations = list(
            base_query.select_for_update()
            .select_related("variant")
            .order_by("variant_id", "pk")
        )
        for reservation in reservations:
            if reservation.status != StockReservation.Status.ACTIVE:
                continue
            balance = balances[str(reservation.variant_id)]
            StockService._apply_delta(
                balance=balance,
                bucket=StockMovement.Bucket.RESERVED,
                delta=-reservation.quantity,
            )
            movement_type = (
                StockMovement.MovementType.RELEASE
                if target_status == StockReservation.Status.RELEASED
                else StockMovement.MovementType.COMMIT
            )
            StockService._append_movement(
                balance=balance,
                movement_type=movement_type,
                bucket=StockMovement.Bucket.RESERVED,
                quantity=-reservation.quantity,
                reference_type=StockMovement.ReferenceType.ORDER,
                reference_id=reference,
                user=user,
            )
            if target_status == StockReservation.Status.RELEASED:
                StockService._apply_delta(
                    balance=balance,
                    bucket=StockMovement.Bucket.AVAILABLE,
                    delta=reservation.quantity,
                )
                StockService._append_movement(
                    balance=balance,
                    movement_type=StockMovement.MovementType.RELEASE,
                    bucket=StockMovement.Bucket.AVAILABLE,
                    quantity=reservation.quantity,
                    reference_type=StockMovement.ReferenceType.ORDER,
                    reference_id=reference,
                    user=user,
                )
            StockReservation.objects.filter(
                pk=reservation.pk,
                status=StockReservation.Status.ACTIVE,
            ).update(status=target_status, updated_at=timezone.now())
            reservation.status = target_status
        return reservations

    @staticmethod
    @transaction.atomic
    def update_threshold(*, variant_id, user, low_stock_threshold: int) -> InventoryBalance:
        shop = _get_seller_shop(user)
        try:
            threshold = int(low_stock_threshold)
        except (TypeError, ValueError) as exc:
            raise BusinessError("Ngưỡng tồn kho phải là số nguyên không âm") from exc
        if threshold < 0:
            raise BusinessError("Ngưỡng tồn kho không được âm")
        variant = (
            ProductVariant.objects.select_related("product", "shop")
            .filter(
                pk=variant_id,
                shop=shop,
                product__shop=shop,
                is_deleted=False,
            )
            .first()
        )
        if variant is None:
            raise BusinessError("Không tìm thấy biến thể", http_status=404)
        balance = StockService._lock_balances([variant])[str(variant.pk)]
        InventoryBalance.objects.filter(pk=balance.pk).update(
            low_stock_threshold=threshold,
            updated_at=timezone.now(),
        )
        balance.refresh_from_db()
        return balance


class StockAlertService:
    @staticmethod
    @transaction.atomic
    def register(*, variant_id, user) -> StockAlert:
        if not _actor_is_active(user) or getattr(user, "role", None) != User.Role.CUSTOMER:
            raise BusinessError("Chỉ Customer mới có thể đăng ký báo khi có hàng", http_status=403)
        variant = (
            ProductVariant.objects.select_related("product", "shop")
            .filter(
                pk=variant_id,
                is_active=True,
                is_deleted=False,
                product__status=Product.Status.APPROVED,
                product__is_deleted=False,
                shop__status=Shop.Status.APPROVED,
                shop__is_deleted=False,
            )
            .first()
        )
        if variant is None:
            raise BusinessError("Không tìm thấy biến thể khả dụng", http_status=404)
        balance = StockService._lock_balances([variant])[str(variant.pk)]
        if balance.available_stock > 0:
            raise BusinessError(
                "Sản phẩm hiện đang có hàng",
                errors={"variant": ["Chỉ có thể đăng ký waitlist khi hết hàng"]},
                http_status=409,
            )
        alert, _ = StockAlert.objects.update_or_create(
            variant=variant,
            user=user,
            defaults={"is_notified": False},
        )
        return alert
