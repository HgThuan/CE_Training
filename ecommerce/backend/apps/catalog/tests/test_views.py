"""API tests for public and administrative catalog views."""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.catalog.models import Brand, Category
from apps.catalog.services import BrandService, CategoryService
from apps.product.tests.factories import ProductFactory


@pytest.mark.django_db
def test_admin_category_crud_and_reorder_api(api_client, admin_user):
    api_client.force_authenticate(admin_user)
    create_response = api_client.post(
        reverse("catalog:admin-category-list"),
        {
            "name": "May tinh",
            "slug": "Computer",
            "sort_order": 3,
        },
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    assert create_response.data["success"] is True
    assert create_response.data["data"]["slug"] == "computer"
    category_id = create_response.data["data"]["id"]

    child = CategoryService.create(name="Laptop")
    reorder_response = api_client.post(
        reverse("catalog:admin-category-reorder"),
        {
            "items": [
                {
                    "id": str(child.pk),
                    "parent_id": category_id,
                    "sort_order": 1,
                }
            ]
        },
        format="json",
    )
    assert reorder_response.status_code == status.HTTP_200_OK
    child.refresh_from_db()
    assert str(child.parent_id) == category_id

    patch_response = api_client.patch(
        reverse("catalog:admin-category-detail", args=[child.pk]),
        {"name": "Laptop gaming", "is_active": False},
        format="json",
    )
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.data["data"]["name"] == "Laptop gaming"
    assert patch_response.data["data"]["is_active"] is False

    delete_response = api_client.delete(
        reverse("catalog:admin-category-detail", args=[child.pk]),
    )
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.data == {
        "success": True,
        "message": "Xóa danh mục thành công",
        "data": {"id": str(child.pk), "is_deleted": True},
    }
    assert Category.objects.get(pk=child.pk).is_deleted is True


@pytest.mark.django_db
def test_admin_brand_crud_api(api_client, admin_user):
    api_client.force_authenticate(admin_user)
    create_response = api_client.post(
        reverse("catalog:admin-brand-list"),
        {
            "name": "Tech Viet",
            "logo_url": "https://cdn.example.com/tech-viet.png",
        },
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    assert create_response.data["data"]["slug"] == "tech-viet"
    brand_id = create_response.data["data"]["id"]

    patch_response = api_client.patch(
        reverse("catalog:admin-brand-detail", args=[brand_id]),
        {"description": "Thuong hieu cong nghe Viet Nam"},
        format="json",
    )
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.data["data"]["description"] == "Thuong hieu cong nghe Viet Nam"

    list_response = api_client.get(reverse("catalog:admin-brand-list"))
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data["meta"]["total_items"] == 1

    delete_response = api_client.delete(
        reverse("catalog:admin-brand-detail", args=[brand_id]),
    )
    assert delete_response.status_code == status.HTTP_200_OK
    assert Brand.objects.get(pk=brand_id).is_deleted is True


@pytest.mark.django_db
def test_public_category_tree_only_returns_active_non_deleted_nodes(api_client):
    root = CategoryService.create(name="Electronics", sort_order=2)
    child = CategoryService.create(name="Phones", parent=root, sort_order=1)
    CategoryService.create(name="Hidden", parent=root, is_active=False)
    deleted = CategoryService.create(name="Deleted")
    CategoryService.soft_delete(category=deleted)
    inactive_root = CategoryService.create(name="Inactive root", is_active=False)
    CategoryService.create(name="Orphaned active child", parent=inactive_root)

    response = api_client.get(reverse("catalog:public-category-tree"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert [item["name"] for item in response.data["data"]] == ["Electronics"]
    assert response.data["data"][0]["children"][0]["id"] == str(child.pk)
    assert response.data["data"][0]["children"][0]["children"] == []


@pytest.mark.django_db
def test_public_brand_list_is_filtered_and_paginated(api_client):
    visible = BrandService.create(name="Visible")
    BrandService.create(name="Inactive", is_active=False)
    deleted = BrandService.create(name="Deleted")
    BrandService.soft_delete(brand=deleted)

    response = api_client.get(reverse("catalog:public-brand-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert [item["id"] for item in response.data["data"]] == [str(visible.pk)]
    assert response.data["meta"] == {
        "page": 1,
        "page_size": 20,
        "total_items": 1,
        "total_pages": 1,
    }


@pytest.mark.django_db
def test_admin_cannot_delete_category_used_by_active_product(api_client, admin_user):
    product = ProductFactory()
    api_client.force_authenticate(admin_user)

    response = api_client.delete(
        reverse(
            "catalog:admin-category-detail",
            args=[product.category_id],
        )
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["success"] is False
    assert "category" in response.data["errors"]
    product.category.refresh_from_db()
    assert product.category.is_deleted is False


@pytest.mark.django_db
@pytest.mark.parametrize("user_fixture", ["customer_user", "seller_user"])
@pytest.mark.parametrize(
    ("method", "route_name", "route_args", "payload"),
    [
        ("post", "catalog:admin-category-list", [], {"name": "Blocked category"}),
        (
            "patch",
            "catalog:admin-category-detail",
            ["category"],
            {"name": "Blocked update"},
        ),
        ("delete", "catalog:admin-category-detail", ["category"], None),
        (
            "post",
            "catalog:admin-category-reorder",
            [],
            {"items": [{"id": "category", "sort_order": 1}]},
        ),
        ("post", "catalog:admin-brand-list", [], {"name": "Blocked brand"}),
        (
            "patch",
            "catalog:admin-brand-detail",
            ["brand"],
            {"name": "Blocked update"},
        ),
        ("delete", "catalog:admin-brand-detail", ["brand"], None),
    ],
)
def test_customer_and_seller_cannot_mutate_catalog(
    request,
    api_client,
    user_fixture,
    method,
    route_name,
    route_args,
    payload,
):
    category = CategoryService.create(name=f"Category {user_fixture} {method} {route_name}")
    brand = BrandService.create(name=f"Brand {user_fixture} {method} {route_name}")
    resolved_args = [
        category.pk if value == "category" else brand.pk if value == "brand" else value
        for value in route_args
    ]
    resolved_payload = payload
    if payload and payload.get("items"):
        resolved_payload = {
            "items": [
                {
                    **item,
                    "id": str(category.pk) if item["id"] == "category" else item["id"],
                }
                for item in payload["items"]
            ]
        }

    api_client.force_authenticate(request.getfixturevalue(user_fixture))
    response = getattr(api_client, method)(
        reverse(route_name, args=resolved_args),
        resolved_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["success"] is False
    assert "errors" in response.data
