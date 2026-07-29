from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.product.models import Product
from apps.product.tests.factories import ProductFactory
from apps.storefront.models import Banner


@pytest.mark.django_db
def test_admin_banner_crud_and_reorder_api(api_client, admin_user):
    api_client.force_authenticate(admin_user)
    create_response = api_client.post(
        reverse("storefront:admin-banner-list"),
        {
            "title": "Hero",
            "image_url": "https://cdn.example.com/hero.webp",
            "sort_order": 1,
        },
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    banner_id = create_response.data["data"]["id"]

    second = Banner.objects.create(
        image_url="https://cdn.example.com/second.webp",
        sort_order=2,
    )
    reorder_response = api_client.post(
        reverse("storefront:admin-banner-reorder"),
        {"source_id": banner_id, "target_id": str(second.pk)},
        format="json",
    )
    assert reorder_response.status_code == status.HTTP_200_OK

    patch_response = api_client.patch(
        reverse("storefront:admin-banner-detail", args=[banner_id]),
        {"title": "Hero updated"},
        format="json",
    )
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.data["data"]["title"] == "Hero updated"

    list_response = api_client.get(reverse("storefront:admin-banner-list"))
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data["meta"]["total_items"] == 2

    delete_response = api_client.delete(reverse("storefront:admin-banner-detail", args=[banner_id]))
    assert delete_response.status_code == status.HTTP_200_OK
    assert Banner.objects.get(pk=banner_id).is_deleted is True


@pytest.mark.django_db
@pytest.mark.parametrize("fixture_name", ["customer_user"])
def test_non_admin_cannot_manage_banners(request, api_client, fixture_name):
    user = request.getfixturevalue(fixture_name)
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("storefront:admin-banner-list"),
        {"image_url": "https://cdn.example.com/blocked.webp"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_anonymous_cannot_manage_banners(api_client):
    response = api_client.get(reverse("storefront:admin-banner-list"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_home_api_returns_only_active_content(api_client):
    now = timezone.now()
    visible = Banner.objects.create(
        title="Visible",
        image_url="https://cdn.example.com/visible.webp",
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(minutes=1),
    )
    Banner.objects.create(
        title="Inactive",
        image_url="https://cdn.example.com/inactive.webp",
        is_active=False,
    )
    product = ProductFactory(status=Product.Status.APPROVED, sold_count=12)

    response = api_client.get(reverse("storefront:home"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert [item["id"] for item in response.data["data"]["banners"]] == [str(visible.pk)]
    assert response.data["data"]["new_arrivals"][0]["id"] == str(product.pk)
    assert response.data["data"]["best_sellers"][0]["id"] == str(product.pk)
    assert response.data["data"]["categories"]
