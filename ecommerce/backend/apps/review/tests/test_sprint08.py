from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import UserFactory
from apps.order.models import ShopOrder
from apps.order.tests.test_services import checkout_fixture
from apps.review.models import Review, ReviewReport
from apps.review.services import ReviewService

pytestmark = pytest.mark.django_db


def completed_order_item():
    user, customer, address, shop, variant, balance, cart_item = checkout_fixture()
    from apps.order.models import Order
    from apps.order.services import CheckoutService

    order, _, _ = CheckoutService.checkout(
        customer=customer,
        cart_item_ids=[cart_item.pk],
        address_id=address.pk,
        coupons={},
        payment_method=Order.PaymentMethod.COD,
        idempotency_key=f"review-{user.pk}",
    )
    shop_order = order.shop_orders.get()
    shop_order.fulfillment_status = ShopOrder.FulfillmentStatus.COMPLETED
    shop_order.completed_at = timezone.now()
    shop_order.save(update_fields=("fulfillment_status", "completed_at", "updated_at"))
    return user, shop, shop_order.items.get()


def test_verified_review_updates_product_rating_and_enforces_one_per_item():
    customer, shop, item = completed_order_item()

    review = ReviewService.create(order_item=item, user=customer, rating=5, content="Rất tốt")

    item.product.refresh_from_db()
    assert review.is_verified_purchase is True
    assert item.product.rating_count == 1
    assert item.product.rating_average == 5
    with pytest.raises(Exception, match="đã được đánh giá"):
        ReviewService.create(order_item=item, user=customer, rating=4)


def test_review_can_only_be_edited_inside_seven_day_window():
    customer, shop, item = completed_order_item()
    review = ReviewService.create(order_item=item, user=customer, rating=3)
    ReviewService.update(review, user=customer, rating=4, content="Cập nhật")
    review.refresh_from_db()
    assert review.rating == 4

    review.editable_until = timezone.now() - timedelta(seconds=1)
    review.save(update_fields=("editable_until", "updated_at"))
    with pytest.raises(Exception, match="hết thời hạn"):
        ReviewService.update(review, user=customer, rating=5)


def test_seller_can_reply_and_report_only_reviews_from_own_shop():
    customer, shop, item = completed_order_item()
    review = ReviewService.create(order_item=item, user=customer, rating=1, content="Spam")

    reply = ReviewService.reply(review, seller=shop.owner, content="Shop đã tiếp nhận")
    report = ReviewService.report(
        review, seller=shop.owner, reason_code="ABUSE", reason_detail="Ngôn từ vi phạm"
    )

    assert reply.review_id == review.pk
    assert report.status == ReviewReport.Status.OPEN
    other_seller = UserFactory(role=User.Role.SELLER)
    with pytest.raises(Exception, match="Không tìm thấy"):
        ReviewService.reply(review, seller=other_seller, content="Không hợp lệ")


def test_admin_hiding_reported_review_recalculates_rating():
    customer, shop, item = completed_order_item()
    review = ReviewService.create(order_item=item, user=customer, rating=1)
    report = ReviewService.report(review, seller=shop.owner, reason_code="SPAM")
    admin = UserFactory(role=User.Role.ADMIN, is_staff=True)

    ReviewService.resolve_report(report, admin=admin, action="HIDE", note="Xác nhận spam")

    review.refresh_from_db()
    item.product.refresh_from_db()
    assert review.status == Review.Status.HIDDEN
    assert item.product.rating_count == 0


def test_review_api_rejects_customer_who_did_not_buy_item():
    customer, shop, item = completed_order_item()
    stranger = UserFactory(role=User.Role.CUSTOMER)
    client = APIClient()
    client.force_authenticate(stranger)

    response = client.post(
        f"/api/v1/order-items/{item.pk}/review",
        {"rating": 5, "content": "Không hợp lệ"},
        format="json",
    )

    assert response.status_code == 404
    assert not Review.objects.exists()


def test_review_role_workflow_is_available_through_the_api():
    customer, shop, item = completed_order_item()
    customer_client = APIClient()
    customer_client.force_authenticate(customer)

    created = customer_client.post(
        f"/api/v1/order-items/{item.pk}/review",
        {"rating": 4, "content": "Sản phẩm tốt"},
        format="json",
    )

    assert created.status_code == 201
    review_id = created.data["data"]["id"]
    order_detail = customer_client.get(f"/api/v1/orders/{item.shop_order.order_id}")
    item_data = order_detail.data["data"]["shop_orders"][0]["items"][0]
    assert item_data["review"]["id"] == review_id

    updated = customer_client.patch(
        f"/api/v1/reviews/{review_id}",
        {"rating": 5, "content": "Cập nhật sau khi sử dụng"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["data"]["rating"] == 5

    seller_client = APIClient()
    seller_client.force_authenticate(shop.owner)
    seller_list = seller_client.get("/api/v1/seller/reviews")
    assert seller_list.status_code == 200
    assert seller_list.data["data"][0]["id"] == review_id

    replied = seller_client.post(
        f"/api/v1/seller/reviews/{review_id}/reply",
        {"content": "Cảm ơn bạn đã đánh giá"},
        format="json",
    )
    assert replied.status_code == 200
    assert replied.data["data"]["reply"]["content"] == "Cảm ơn bạn đã đánh giá"

    reported = seller_client.post(
        f"/api/v1/seller/reviews/{review_id}/report",
        {"reason_code": "INAPPROPRIATE", "reason_detail": "Cần Admin kiểm tra"},
        format="json",
    )
    assert reported.status_code == 201

    admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
    admin_client = APIClient()
    admin_client.force_authenticate(admin)
    reports = admin_client.get("/api/v1/admin/review-reports")
    assert reports.status_code == 200
    report_id = reports.data["data"][0]["id"]

    resolved = admin_client.post(
        f"/api/v1/admin/review-reports/{report_id}/resolve",
        {"action": "KEEP", "note": "Đánh giá hợp lệ"},
        format="json",
    )
    assert resolved.status_code == 200
    assert resolved.data["data"]["status"] == ReviewReport.Status.REJECTED
