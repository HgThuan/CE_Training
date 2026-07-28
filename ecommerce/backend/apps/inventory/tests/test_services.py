from concurrent.futures import ThreadPoolExecutor

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, connections

from apps.account.models import Notification, User
from apps.account.tests.factories import UserFactory
from apps.common.exceptions import BusinessError
from apps.inventory.exceptions import InsufficientStockError
from apps.inventory.models import (
    InventoryBalance,
    StockAlert,
    StockEntry,
    StockMovement,
    StockOutEntry,
    StockReservation,
)
from apps.inventory.services import StockAlertService, StockService
from apps.product.models import Product

pytestmark = pytest.mark.django_db


def _stock_entry_payload(variant, *, quantity=5):
    return {
        "supplier_name": "Công ty Phân phối A",
        "note": "Nhập lô tháng 7",
        "items": [
            {
                "variant_id": variant.pk,
                "quantity": quantity,
                "unit_cost": "45000",
            }
        ],
    }


def test_confirm_stock_entry_increases_available_and_appends_ledger(
    seller_a,
    variant_a,
):
    entry = StockService.create_stock_entry(
        user=seller_a,
        data=_stock_entry_payload(variant_a, quantity=7),
    )

    confirmed = StockService.confirm_stock_entry(entry.pk, seller_a)

    balance = InventoryBalance.objects.get(variant=variant_a)
    movement = StockMovement.objects.get(
        variant=variant_a,
        reference_type=StockMovement.ReferenceType.STOCK_ENTRY,
    )
    assert confirmed.status == StockEntry.Status.CONFIRMED
    assert confirmed.confirmed_by == seller_a
    assert balance.available_stock == 7
    assert movement.quantity == 7
    assert movement.balance_after == 7
    assert movement.bucket == StockMovement.Bucket.AVAILABLE


def test_confirm_stock_entry_cannot_run_twice(seller_a, variant_a):
    entry = StockService.create_stock_entry(
        user=seller_a,
        data=_stock_entry_payload(variant_a),
    )
    StockService.confirm_stock_entry(entry.pk, seller_a)

    with pytest.raises(BusinessError, match="đã được xác nhận"):
        StockService.confirm_stock_entry(entry.pk, seller_a)

    assert InventoryBalance.objects.get(variant=variant_a).available_stock == 5
    assert StockMovement.objects.filter(variant=variant_a).count() == 1


def test_confirmed_stock_entry_cannot_be_edited(seller_a, variant_a):
    entry = StockService.create_stock_entry(
        user=seller_a,
        data=_stock_entry_payload(variant_a),
    )
    StockService.confirm_stock_entry(entry.pk, seller_a)

    with pytest.raises(BusinessError, match="Không thể sửa"):
        StockService.update_stock_entry(
            stock_entry_id=entry.pk,
            user=seller_a,
            data={"note": "Không được phép"},
        )


def test_confirm_stock_out_rejects_negative_balance_and_rolls_back(
    seller_a,
    balance_a,
):
    entry = StockService.create_stock_out_entry(
        user=seller_a,
        data={
            "entry_type": StockOutEntry.EntryType.OUT,
            "reason": "Hàng hỏng",
            "items": [{"variant_id": balance_a.variant_id, "quantity": 11}],
        },
    )

    with pytest.raises(InsufficientStockError):
        StockService.confirm_stock_out(entry.pk, seller_a)

    balance_a.refresh_from_db()
    entry.refresh_from_db()
    assert balance_a.available_stock == 10
    assert entry.status == StockOutEntry.Status.DRAFT
    assert not StockMovement.objects.filter(
        reference_type=StockMovement.ReferenceType.STOCK_OUT,
        reference_id=str(entry.pk),
    ).exists()


def test_adjustment_uses_new_physical_count(seller_a, balance_a):
    entry = StockService.create_stock_out_entry(
        user=seller_a,
        data={
            "entry_type": StockOutEntry.EntryType.ADJUSTMENT,
            "reason": "Kiểm kê cuối ngày",
            "items": [{"variant_id": balance_a.variant_id, "quantity": 4}],
        },
    )

    StockService.confirm_stock_out(entry.pk, seller_a)

    balance_a.refresh_from_db()
    movement = StockMovement.objects.get(
        reference_type=StockMovement.ReferenceType.ADJUSTMENT,
        reference_id=str(entry.pk),
    )
    assert balance_a.available_stock == 4
    assert movement.quantity == -6
    assert movement.balance_after == 4


def test_out_crossing_threshold_notifies_seller(seller_a, balance_a):
    entry = StockService.create_stock_out_entry(
        user=seller_a,
        data={
            "entry_type": StockOutEntry.EntryType.OUT,
            "reason": "Xuất bán lẻ",
            "items": [{"variant_id": balance_a.variant_id, "quantity": 5}],
        },
    )

    StockService.confirm_stock_out(entry.pk, seller_a)

    notification = Notification.objects.get(
        user=seller_a,
        kind=Notification.Kind.INVENTORY_LOW_STOCK,
    )
    assert notification.metadata["available_stock"] == 5


def test_reserve_release_is_idempotent(customer, balance_a):
    first = StockService.reserve_stock(
        balance_a.variant,
        4,
        "ORDER-001",
        customer,
    )
    retry = StockService.reserve_stock(
        balance_a.variant,
        4,
        "ORDER-001",
        customer,
    )
    assert retry.pk == first.pk

    first_release = StockService.release_stock("ORDER-001", customer)
    second_release = StockService.release_stock("ORDER-001", customer)

    balance_a.refresh_from_db()
    first.refresh_from_db()
    assert first.status == StockReservation.Status.RELEASED
    assert balance_a.available_stock == 10
    assert balance_a.reserved_stock == 0
    assert len(first_release) == len(second_release) == 1
    assert StockMovement.objects.filter(
        reference_id="ORDER-001",
        movement_type=StockMovement.MovementType.RELEASE,
    ).count() == 2


def test_commit_is_idempotent_and_does_not_restore_available(customer, balance_a):
    StockService.reserve_stock(balance_a.variant, 3, "ORDER-002", customer)

    StockService.commit_stock("ORDER-002", customer)
    StockService.commit_stock("ORDER-002", customer)

    balance_a.refresh_from_db()
    reservation = StockReservation.objects.get(order_reference="ORDER-002")
    assert reservation.status == StockReservation.Status.COMMITTED
    assert balance_a.available_stock == 7
    assert balance_a.reserved_stock == 0
    assert StockMovement.objects.filter(
        reference_id="ORDER-002",
        movement_type=StockMovement.MovementType.COMMIT,
    ).count() == 1


def test_reserve_rejects_insufficient_stock(customer, balance_a):
    with pytest.raises(InsufficientStockError):
        StockService.reserve_stock(balance_a.variant, 11, "ORDER-003", customer)

    balance_a.refresh_from_db()
    assert balance_a.available_stock == 10
    assert balance_a.reserved_stock == 0
    assert not StockReservation.objects.filter(order_reference="ORDER-003").exists()


def test_waitlist_is_notified_when_entry_restocks(
    seller_a,
    customer,
    variant_a,
):
    variant_a.product.status = Product.Status.APPROVED
    variant_a.product.save(update_fields=["status", "updated_at"])
    StockAlertService.register(variant_id=variant_a.pk, user=customer)
    entry = StockService.create_stock_entry(
        user=seller_a,
        data=_stock_entry_payload(variant_a, quantity=2),
    )

    StockService.confirm_stock_entry(entry.pk, seller_a)

    alert = StockAlert.objects.get(variant=variant_a, user=customer)
    assert alert.is_notified is True
    assert Notification.objects.filter(
        user=customer,
        kind=Notification.Kind.BACK_IN_STOCK,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_reservations_never_oversell(balance_a):
    if not connection.features.has_select_for_update:
        pytest.skip("Concurrency lock test requires PostgreSQL SELECT FOR UPDATE")

    variant_id = balance_a.variant_id
    user_ids = [
        UserFactory(role=User.Role.CUSTOMER).pk,
        UserFactory(role=User.Role.CUSTOMER).pk,
    ]

    def reserve(user_id, reference):
        connections.close_all()
        try:
            user = get_user_model().objects.get(pk=user_id)
            StockService.reserve_stock(variant_id, 7, reference, user)
            return True
        except InsufficientStockError:
            return False
        finally:
            # Thread-local connections must be closed explicitly or PostgreSQL cannot
            # drop the test database during teardown.
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda args: reserve(*args),
                [(user_ids[0], "ORDER-A"), (user_ids[1], "ORDER-B")],
            )
        )

    balance = InventoryBalance.objects.get(pk=balance_a.pk)
    reserved_total = StockReservation.objects.filter(
        status=StockReservation.Status.ACTIVE
    ).values_list("quantity", flat=True)
    assert sum(reserved_total) <= 10
    assert balance.available_stock >= 0
    assert results.count(True) == 1
