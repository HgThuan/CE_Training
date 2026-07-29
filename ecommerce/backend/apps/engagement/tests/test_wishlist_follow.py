from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.account.models import Shop, User
from apps.account.tests.factories import UserFactory
from apps.engagement.models import ShopFollower, Wishlist, WishlistItem
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


def wishlist_url() -> str:
    return reverse("engagement:wishlist-list")


def wishlist_toggle_url() -> str:
    return reverse("engagement:wishlist-toggle")


def follow_url(shop) -> str:
    return reverse(
        "engagement:shop-follow-toggle",
        kwargs={"shop_id": shop.pk},
    )


def public_shop_url(shop) -> str:
    return reverse("account:public-shop", kwargs={"slug": shop.slug})


def test_wishlist_and_follow_constraints(customer, other_customer, product, shop):
    wishlist = Wishlist.objects.create(user=customer)
    WishlistItem.objects.create(
        wishlist=wishlist,
        product=product,
        price_when_added=Decimal("100000"),
    )
    ShopFollower.objects.create(shop=shop, user=customer)

    with pytest.raises(IntegrityError), transaction.atomic():
        Wishlist.objects.create(user=customer)
    with pytest.raises(IntegrityError), transaction.atomic():
        WishlistItem.objects.create(wishlist=wishlist, product=product)
    with pytest.raises(IntegrityError), transaction.atomic():
        ShopFollower.objects.create(shop=shop, user=customer)
    with pytest.raises(IntegrityError), transaction.atomic():
        WishlistItem.objects.create(
            wishlist=Wishlist.objects.create(user=other_customer),
            product=ProductFactory(status=Product.Status.APPROVED),
            price_when_added=Decimal("-1"),
        )


def test_wishlist_get_is_owner_scoped_paginated_and_public_only(
    api_client,
    customer,
    other_customer,
    shop,
):
    visible = ProductFactory(
        shop=shop,
        status=Product.Status.APPROVED,
        min_price=Decimal("125000"),
        max_price=Decimal("125000"),
    )
    hidden = ProductFactory(
        shop=shop,
        status=Product.Status.HIDDEN,
    )
    other_product = ProductFactory(status=Product.Status.APPROVED)
    own_wishlist = Wishlist.objects.create(user=customer)
    WishlistItem.objects.create(wishlist=own_wishlist, product=visible)
    WishlistItem.objects.create(wishlist=own_wishlist, product=hidden)
    WishlistItem.objects.create(
        wishlist=Wishlist.objects.create(user=other_customer),
        product=other_product,
    )
    api_client.force_authenticate(customer)

    response = api_client.get(wishlist_url(), {"page_size": 1})

    assert response.status_code == 200
    assert response.data["meta"] == {
        "page": 1,
        "page_size": 1,
        "total_items": 1,
        "total_pages": 1,
    }
    assert response.data["data"][0]["product"]["id"] == str(visible.pk)
    serialized = str(response.data)
    assert shop.owner.email not in serialized
    assert "cost_price" not in serialized
    assert "barcode" not in serialized
    assert str(other_product.pk) not in serialized


def test_empty_wishlist_get_does_not_create_one(api_client, customer):
    api_client.force_authenticate(customer)

    response = api_client.get(wishlist_url())

    assert response.status_code == 200
    assert response.data["data"] == []
    assert response.data["meta"]["total_items"] == 0
    assert not Wishlist.objects.filter(user=customer).exists()


def test_wishlist_toggle_adds_price_snapshot_then_removes(api_client, customer, product):
    product.min_price = Decimal("990000")
    product.max_price = Decimal("990000")
    product.save(update_fields=("min_price", "max_price", "updated_at"))
    api_client.force_authenticate(customer)

    added = api_client.post(
        wishlist_toggle_url(),
        {"product_id": str(product.pk)},
        format="json",
    )
    product.min_price = Decimal("790000")
    product.save(update_fields=("min_price", "updated_at"))
    item = WishlistItem.objects.get(wishlist__user=customer, product=product)
    removed = api_client.post(
        wishlist_toggle_url(),
        {"product_id": str(product.pk)},
        format="json",
    )

    assert added.status_code == 200
    assert added.data["data"]["is_wishlisted"] is True
    assert added.data["data"]["item"]["price_when_added"] == "990000"
    assert item.price_when_added == Decimal("990000")
    assert removed.status_code == 200
    assert removed.data["data"] == {
        "product_id": str(product.pk),
        "is_wishlisted": False,
        "item": None,
    }
    assert Wishlist.objects.filter(user=customer).count() == 1
    assert not WishlistItem.objects.filter(wishlist__user=customer).exists()


def test_wishlist_rejects_guest_wrong_role_inactive_and_non_public_product(
    api_client,
    customer,
    seller,
    shop,
):
    draft = ProductFactory(shop=shop, status=Product.Status.DRAFT)
    guest = api_client.post(
        wishlist_toggle_url(),
        {"product_id": str(draft.pk)},
        format="json",
    )
    api_client.force_authenticate(seller)
    wrong_role = api_client.get(wishlist_url())
    inactive = UserFactory(role=User.Role.CUSTOMER, is_active=False)
    api_client.force_authenticate(inactive)
    inactive_response = api_client.get(wishlist_url())
    api_client.force_authenticate(customer)
    draft_response = api_client.post(
        wishlist_toggle_url(),
        {"product_id": str(draft.pk)},
        format="json",
    )
    missing_response = api_client.post(
        wishlist_toggle_url(),
        {"product_id": str(uuid4())},
        format="json",
    )
    unknown_field = api_client.post(
        wishlist_toggle_url(),
        {"product_id": str(draft.pk), "user_id": customer.pk},
        format="json",
    )

    assert guest.status_code == 401
    assert wrong_role.status_code == 403
    assert inactive_response.status_code == 403
    assert draft_response.status_code == 404
    assert missing_response.status_code == 404
    assert unknown_field.status_code == 400
    assert Wishlist.objects.count() == 0


def test_follow_toggle_and_public_shop_state_are_customer_scoped(
    api_client,
    customer,
    other_customer,
    shop,
):
    api_client.force_authenticate(customer)
    followed = api_client.post(follow_url(shop), {}, format="json")
    authenticated_shop = api_client.get(public_shop_url(shop))
    api_client.force_authenticate(other_customer)
    other_customer_shop = api_client.get(public_shop_url(shop))
    api_client.force_authenticate(user=None)
    anonymous_shop = api_client.get(public_shop_url(shop))
    api_client.force_authenticate(customer)
    unfollowed = api_client.post(follow_url(shop), {}, format="json")

    assert followed.status_code == 200
    assert followed.data["data"] == {
        "shop_id": shop.pk,
        "is_following": True,
        "follower_count": 1,
    }
    assert authenticated_shop.data["data"]["shop"]["is_following"] is True
    assert other_customer_shop.data["data"]["shop"]["is_following"] is False
    assert anonymous_shop.data["data"]["shop"]["is_following"] is False
    assert anonymous_shop.data["data"]["shop"]["follower_count"] == 1
    assert unfollowed.data["data"]["is_following"] is False
    assert unfollowed.data["data"]["follower_count"] == 0


def test_follow_rejects_guest_wrong_role_invalid_shop_and_unknown_body(
    api_client,
    customer,
    seller,
    shop,
):
    guest = api_client.post(follow_url(shop), {}, format="json")
    api_client.force_authenticate(seller)
    wrong_role = api_client.post(follow_url(shop), {}, format="json")
    api_client.force_authenticate(customer)
    unknown_body = api_client.post(
        follow_url(shop),
        {"user_id": customer.pk},
        format="json",
    )
    shop.status = Shop.Status.LOCKED
    shop.save(update_fields=("status", "updated_at"))
    locked = api_client.post(follow_url(shop), {}, format="json")

    assert guest.status_code == 401
    assert wrong_role.status_code == 403
    assert unknown_body.status_code == 400
    assert locked.status_code == 404
    assert ShopFollower.objects.count() == 0


def test_public_shop_is_privacy_safe_and_returns_sorted_public_products(
    api_client,
    customer,
    shop,
):
    low_price = ProductFactory(
        shop=shop,
        status=Product.Status.APPROVED,
        name="Sản phẩm giá thấp",
        min_price=Decimal("100000"),
        max_price=Decimal("100000"),
    )
    high_price = ProductFactory(
        shop=shop,
        status=Product.Status.APPROVED,
        name="Sản phẩm giá cao",
        min_price=Decimal("500000"),
        max_price=Decimal("500000"),
    )
    ProductFactory(shop=shop, status=Product.Status.DRAFT)
    ProductFactory(status=Product.Status.APPROVED)
    ShopFollower.objects.create(shop=shop, user=customer)

    response = api_client.get(
        public_shop_url(shop),
        {"sort": "price_desc", "page_size": 1},
    )

    assert response.status_code == 200
    assert set(response.data["data"]["shop"]) == {
        "id",
        "name",
        "slug",
        "description",
        "logo_url",
        "cover_url",
        "average_rating",
        "total_products",
        "follower_count",
        "is_following",
        "created_at",
    }
    assert response.data["data"]["shop"]["total_products"] == 2
    assert response.data["data"]["shop"]["follower_count"] == 1
    assert response.data["data"]["products"][0]["id"] == str(high_price.pk)
    assert response.data["meta"] == {
        "page": 1,
        "page_size": 1,
        "total_items": 2,
        "total_pages": 2,
    }
    serialized = str(response.data)
    assert shop.owner.email not in serialized
    assert "owner_id" not in response.data["data"]["shop"]
    assert "lock_reason" not in response.data["data"]["shop"]
    assert str(low_price.pk) not in serialized


def test_public_shop_excludes_products_with_inactive_category(api_client, shop):
    visible = ProductFactory(shop=shop, status=Product.Status.APPROVED)
    hidden = ProductFactory(shop=shop, status=Product.Status.APPROVED)
    hidden.category.is_active = False
    hidden.category.save(update_fields=("is_active", "updated_at"))

    response = api_client.get(public_shop_url(shop), {"page_size": 10})

    assert response.status_code == 200
    product_ids = {item["id"] for item in response.data["data"]["products"]}
    assert str(visible.pk) in product_ids
    assert str(hidden.pk) not in product_ids
    assert response.data["data"]["shop"]["total_products"] == 1
